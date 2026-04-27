"""
Fonctions de régression linéaire pour l'analyse immobilière.

Aucune dépendance Streamlit — 100 % testable avec pytest sans lancer l'UI.
IMPORTANT : pur Python (listes, boucles) — pas de numpy ni sklearn.
"""
from __future__ import annotations

import math
import pandas as pd

from config import DVF_REGRESSION


# ── Primitives OLS (from scratch — pur Python) ──────────────────────────────────

def least_squares_fit(x: list, y: list) -> tuple[float, float]:
    """Régression OLS univariée y ~ x.  Retourne (slope, intercept)."""
    n = len(x)
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    denom = sum((xi - x_mean) ** 2 for xi in x)
    if denom == 0:
        return 0.0, y_mean
    slope     = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / denom
    intercept = y_mean - slope * x_mean
    return slope, intercept


def r_squared(x: list, y: list, slope: float, intercept: float) -> float:
    """
    Coefficient de détermination R² = 1 − SS_res / SS_tot.
    Robuste aux NaN : filtre automatiquement les paires invalides.
    """
    pairs = [
        (xi, yi) for xi, yi in zip(x, y)
        if xi is not None and yi is not None
        and not math.isnan(float(xi)) and not math.isnan(float(yi))
    ]
    if len(pairs) < 2:
        return 0.0
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    y_mean = sum(ys) / len(ys)
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(xs, ys))
    ss_tot = sum((yi - y_mean) ** 2 for yi in ys)
    return 0.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot


def compute_regression(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Régression linéaire prix ~ surface par type de bien (pure pandas, sans numpy/scipy).

    Enrichit le DataFrame avec :
      - prix_predit    : prix attendu selon la droite de régression
      - ecart          : prix réel − prix prédit  (négatif = sous-évalué)
      - ecart_pct      : écart en % du prix prédit
      - _slope / _intercept : coefficients pour tracer la droite
    """
    results = []
    for ttype, grp in df_input.groupby("type_local"):
        grp = grp.dropna(subset=["valeur_fonciere", "surface_reelle_bati"]).copy().reset_index(drop=True)
        grp = grp[(grp["surface_reelle_bati"] > 10) & (grp["valeur_fonciere"] > 10_000)]

        if len(grp) < 2:
            for col in ["prix_predit", "ecart", "ecart_pct", "_slope", "_intercept"]:
                grp[col] = float("nan")
            results.append(grp)
            continue

        x, y  = grp["surface_reelle_bati"], grp["valeur_fonciere"]
        n     = len(x)
        denom = n * (x ** 2).sum() - x.sum() ** 2

        if denom == 0:
            slope, intercept = 0.0, float(y.mean())
        else:
            slope     = (n * (x * y).sum() - x.sum() * y.sum()) / denom
            intercept = (y.sum() - slope * x.sum()) / n

        grp["_slope"]      = slope
        grp["_intercept"]  = intercept
        grp["prix_predit"] = (slope * x + intercept).round(0)
        grp["ecart"]       = (y - grp["prix_predit"]).round(0)
        grp["ecart_pct"]   = (grp["ecart"] / grp["prix_predit"] * 100).round(1)
        results.append(grp)

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def compute_dvf_scores(
    df_input: pd.DataFrame,
    models: dict | None = None,
) -> pd.DataFrame:
    """
    Applique les coefficients DVF (calculés dynamiquement ou fallback config)
    à chaque annonce pour évaluer son écart vs le marché historique.

    Paramètres
    ----------
    df_input : DataFrame des annonces (doit contenir type_local,
               surface_reelle_bati, valeur_fonciere).
    models   : dict {"Appartement": {"slope": …, "intercept": …}, …}
               Si None, utilise DVF_REGRESSION (valeurs de repli de config.py).

    Colonnes ajoutées
    -----------------
      dvf_prix_predit  : prix attendu selon le modèle DVF
      dvf_ecart        : prix réel − dvf_prix_predit  (négatif = bonne affaire)
      dvf_ecart_pct    : écart en %
      _dvf_slope / _dvf_intercept : coefficients utilisés (pour tracer la droite)
    """
    _models = models if models is not None else DVF_REGRESSION

    df = df_input.copy().reset_index(drop=True)
    for col in ["dvf_prix_predit", "dvf_ecart", "dvf_ecart_pct", "_dvf_slope", "_dvf_intercept"]:
        df[col] = float("nan")

    for ttype, coef in _models.items():
        mask = (
            df["type_local"].eq(ttype)
            & df["surface_reelle_bati"].notna()
            & df["valeur_fonciere"].notna()
            & (df["surface_reelle_bati"] > 10)
            & (df["valeur_fonciere"] > 10_000)
        )
        if not mask.any():
            continue
        x = df.loc[mask, "surface_reelle_bati"]
        y = df.loc[mask, "valeur_fonciere"]
        predicted = (coef["slope"] * x + coef["intercept"]).round(0)
        df.loc[mask, "_dvf_slope"]      = coef["slope"]
        df.loc[mask, "_dvf_intercept"]  = coef["intercept"]
        df.loc[mask, "dvf_prix_predit"] = predicted
        df.loc[mask, "dvf_ecart"]       = (y - predicted).round(0)
        df.loc[mask, "dvf_ecart_pct"]   = ((y - predicted) / predicted * 100).round(1)

    return df


# ── Constantes encodage DPE ───────────────────────────────────────────────────
DPE_NUMERIC: dict[str, int] = {"A": 7, "B": 6, "C": 5, "D": 4, "E": 3, "F": 2, "G": 1}


# ── Helpers statistiques from scratch (pur Python, sans numpy) ────────────────

def _mean_list(xs: list) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std_list(xs: list) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean_list(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def _normalize_col(xs: list) -> tuple:
    """Retourne (valeurs normalisées, moyenne, écart-type)."""
    m = _mean_list(xs)
    s = _std_list(xs)
    if s < 1e-10:
        return [0.0] * len(xs), m, 1.0
    return [(x - m) / s for x in xs], m, s


# ── Scoring par quartier ──────────────────────────────────────────────────────

def compute_neighborhood_scores(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Identifie les opportunités selon l'écart au prix/m² moyen du quartier.
    From scratch — mean et standard_deviation en pur Python (listes).

    Seuil opportunité : prix_m2 < moyenne_quartier − 1.5 × écart_type

    Colonnes ajoutées :
      qrt_mean_pm2    : prix/m² moyen du quartier
      qrt_std_pm2     : écart-type du prix/m² dans le quartier
      qrt_prix_predit : prix "attendu" = mean_pm2 × surface
      qrt_ecart       : économie en € (négatif = sous-évalué)
      qrt_ecart_pct   : écart en % par rapport au prix attendu
    """
    df = df_input.copy().reset_index(drop=True)
    for col in ["qrt_mean_pm2", "qrt_std_pm2", "qrt_prix_predit", "qrt_ecart", "qrt_ecart_pct"]:
        df[col] = float("nan")

    valid_mask = (
        df["prix_m2"].notna()
        & df["nom_commune"].notna()
        & df["surface_reelle_bati"].notna()
        & df["valeur_fonciere"].notna()
        & (df["prix_m2"] > 0)
    )
    valid = df[valid_mask]

    for quartier, grp in valid.groupby("nom_commune"):
        pm2_list = [float(v) for v in grp["prix_m2"].tolist()]
        if len(pm2_list) < 3:
            continue

        # Statistiques from scratch (pur Python)
        m = _mean_list(pm2_list)
        s = _std_list(pm2_list)

        idx = grp.index
        prix_attendus = (df.loc[idx, "surface_reelle_bati"] * m).round(0)
        prix_reels    = df.loc[idx, "valeur_fonciere"]

        df.loc[idx, "qrt_mean_pm2"]    = round(m, 0)
        df.loc[idx, "qrt_std_pm2"]     = round(s, 0)
        df.loc[idx, "qrt_prix_predit"] = prix_attendus
        df.loc[idx, "qrt_ecart"]       = (prix_reels - prix_attendus).round(0)
        df.loc[idx, "qrt_ecart_pct"]   = (
            (prix_reels - prix_attendus) / prix_attendus * 100
        ).round(1)

    return df


# ── Régression multivariée — descente de gradient (from scratch) ─────────────

def _gradient_descent(
    X: list,
    y: list,
    lr: float = 0.05,
    epochs: int = 300,
) -> tuple:
    """
    Descente de gradient pour régression multivariée.
    Pur Python — sans numpy ni sklearn.

    X      : liste de vecteurs de features (normalisés)
    y      : liste de cibles (normalisées)
    Retourne (biais, [coefficients]).
    """
    n = len(y)
    k = len(X[0]) if X else 0
    bias = 0.0
    w    = [0.0] * k

    for _ in range(epochs):
        preds  = [bias + sum(w[j] * X[i][j] for j in range(k)) for i in range(n)]
        errors = [preds[i] - y[i] for i in range(n)]
        bias  -= lr * sum(errors) / n
        for j in range(k):
            w[j] -= lr * sum(errors[i] * X[i][j] for i in range(n)) / n

    return bias, w


def compute_multivariate_regression(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Régression multivariée Prix ~ Surface + Pièces [+ DPE numérique]
    par descente de gradient (from scratch, sans sklearn).

    Colonnes ajoutées :
      mv_prix_predit : prix prédit par le modèle multivarié
      mv_ecart       : prix réel − prix prédit
      mv_ecart_pct   : écart en %
      mv_r2          : R² du modèle par type de bien
    """
    results = []

    for ttype, grp in df_input.groupby("type_local"):
        # reset_index évite le bug "cannot reindex on an axis with duplicate labels"
        # qui survient quand df_input a des index dupliqués (après merges)
        grp = grp.copy().reset_index(drop=True)
        for col in ["mv_prix_predit", "mv_ecart", "mv_ecart_pct", "mv_r2"]:
            grp[col] = float("nan")

        # Encodage DPE
        if "dpe" in grp.columns:
            grp["_dpe_num"] = grp["dpe"].map(DPE_NUMERIC)
        else:
            grp["_dpe_num"] = float("nan")

        # Features de base toujours disponibles
        feat_cols = ["surface_reelle_bati", "nombre_pieces_principales"]
        # Ajouter DPE si couverture suffisante (>30 %)
        if grp["_dpe_num"].notna().sum() > len(grp) * 0.3:
            feat_cols.append("_dpe_num")

        required = ["valeur_fonciere"] + feat_cols
        clean = grp.dropna(subset=required).copy()
        clean = clean[
            (clean["surface_reelle_bati"] > 10) &
            (clean["valeur_fonciere"] > 10_000)
        ]

        if len(clean) < 10:
            results.append(grp.drop(columns=["_dpe_num"], errors="ignore"))
            continue

        # Construire X et y en listes Python pures
        X_raw = [[float(clean[f].iloc[i]) for f in feat_cols] for i in range(len(clean))]
        y_raw = [float(v) for v in clean["valeur_fonciere"].tolist()]

        # Normalisation colonne par colonne
        n_feat   = len(feat_cols)
        X_cols   = [[X_raw[i][j] for i in range(len(X_raw))] for j in range(n_feat)]
        scalers  = []
        X_norm_cols = []
        for col_vals in X_cols:
            normed, m, s = _normalize_col(col_vals)
            X_norm_cols.append(normed)
            scalers.append((m, s))

        y_normed, y_mean, y_std = _normalize_col(y_raw)

        # Reconstruction de la matrice X normalisée
        X_norm = [[X_norm_cols[j][i] for j in range(n_feat)] for i in range(len(X_raw))]

        # Descente de gradient
        bias_n, w_n = _gradient_descent(X_norm, y_normed, lr=0.05, epochs=300)

        # Prédictions dénormalisées
        preds = [
            (bias_n + sum(w_n[j] * X_norm[i][j] for j in range(n_feat))) * y_std + y_mean
            for i in range(len(X_norm))
        ]

        # R²
        y_mean_v = _mean_list(y_raw)
        ss_tot = sum((yi - y_mean_v) ** 2 for yi in y_raw)
        ss_res = sum((yi - pi) ** 2 for yi, pi in zip(y_raw, preds))
        r2 = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        clean = clean.copy()
        clean["mv_prix_predit"] = [round(p, 0) for p in preds]
        clean["mv_ecart"]       = (clean["valeur_fonciere"] - clean["mv_prix_predit"]).round(0)
        clean["mv_ecart_pct"]   = (clean["mv_ecart"] / clean["mv_prix_predit"] * 100).round(1)
        clean["mv_r2"]          = round(r2, 3)

        grp.update(clean[["mv_prix_predit", "mv_ecart", "mv_ecart_pct", "mv_r2"]])
        results.append(grp.drop(columns=["_dpe_num"], errors="ignore"))

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()
