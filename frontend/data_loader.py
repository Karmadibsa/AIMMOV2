"""
Chargement et pré-traitement des données immobilières.

Priorité des sources :
  1. Supabase  — si SUPABASE_URL + SUPABASE_KEY sont définis (prod / GitHub Actions)
  2. CSV local — data/annonces.csv (fallback dev / hors-ligne)

Cache Streamlit (TTL 5 min) pour éviter les rechargements fréquents.
"""

import os

import pandas as pd
import streamlit as st

from config import CSV_PATH, DVF_CSV_PATH, DVF_PM2_FILTERS, DVF_REGRESSION
from analysis.regression import least_squares_fit, r_squared
from ui.components import build_tags_from_row

# ── Mapping colonnes Supabase → noms attendus par l'app ──────────────────────
# La table Supabase utilise des noms courts ; l'app utilise le schéma DVF.
SUPABASE_COL_MAP: dict[str, str] = {
    "lien":      "url",
    "prix":      "valeur_fonciere",
    "surface":   "surface_reelle_bati",
    "pieces":    "nombre_pieces_principales",
    "quartier":  "nom_commune",
    "type_bien": "type_local",
    # "titre", "source", "description" gardent leur nom
}


# ── Chargement principal ──────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """
    Charge les annonces depuis Supabase (prod) ou le CSV local (dev/fallback).
    Retourne un DataFrame vide si aucune source n'est disponible.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    df = pd.DataFrame()

    # ── Source 1 : Supabase ──────────────────────────────────────────────────
    if supabase_url and supabase_key:
        try:
            from supabase import create_client  # import tardif — pas requis en dev

            client = create_client(supabase_url, supabase_key)

            # Pagination : Supabase limite à 1 000 lignes par requête
            PAGE  = 1_000
            rows  = []
            start = 0
            while True:
                batch = (
                    client.table("annonces")
                    .select("*")
                    .range(start, start + PAGE - 1)
                    .execute()
                ).data or []
                rows.extend(batch)
                if len(batch) < PAGE:
                    break
                start += PAGE

            if rows:
                df = pd.DataFrame(rows)
                df = df.rename(columns=SUPABASE_COL_MAP)

        except Exception as e:
            st.warning(f"⚠️ Supabase indisponible ({e}). Utilisation du CSV local.")

    # ── Source 2 : CSV local (fallback) ─────────────────────────────────────
    if df.empty:
        if not CSV_PATH.exists():
            return pd.DataFrame()
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # ── Post-traitement commun ────────────────────────────────────────────────
    return _process(df)


def _process(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage et enrichissement communs (Supabase ou CSV)."""

    # Filtre : types de bien pertinents uniquement (exclut Programme, terrain, etc.)
    if "type_local" in df.columns:
        df = df[df["type_local"].isin(["Appartement", "Maison"])].copy()

    # Conversion numérique
    for col in ("valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Suppression des aberrations
    if "valeur_fonciere" in df.columns:
        df = df[~((df["valeur_fonciere"].notna()) & (df["valeur_fonciere"] < 1_000))].copy()
    if "surface_reelle_bati" in df.columns:
        df = df[~((df["surface_reelle_bati"].notna()) & (df["surface_reelle_bati"] < 9))].copy()

    # Prix au m²
    mask = df["surface_reelle_bati"].fillna(0) > 0
    df["prix_m2"] = float("nan")
    df.loc[mask, "prix_m2"] = (
        df.loc[mask, "valeur_fonciere"] / df.loc[mask, "surface_reelle_bati"]
    ).round(0)
    df["prix_m2"] = pd.to_numeric(df["prix_m2"], errors="coerce")

    # Date de mise à jour : date_publication (Supabase) ou date_mutation (CSV)
    for date_col in ("date_publication", "date_scraped", "date_mutation"):
        if date_col in df.columns:
            df["date_mutation"] = pd.to_datetime(df[date_col], errors="coerce")
            break

    # Tags : colonnes booléennes Supabase en priorité, texte en complément
    df["tags"] = [build_tags_from_row(row) for row in df.to_dict("records")]

    # DPE / GES / énergie — proviennent directement de l'API BienIci via Supabase.
    # On ne complète PAS par heuristiques textuelles : si la valeur est NULL en base,
    # c'est qu'elle est inconnue → on laisse NaN pour ne pas afficher de fausse info.
    for col in ("dpe", "ges"):
        if col in df.columns:
            df[col] = df[col].where(df[col].isin(list("ABCDEFG")), other=None)

    if "energie_valeur" in df.columns:
        df["energie_valeur"] = pd.to_numeric(df["energie_valeur"], errors="coerce")

    return df


# ── Données DVF brutes (pour analyses de tendance) ───────────────────────────

@st.cache_data(ttl=3600)
def load_dvf_raw(dvf_csv_path: str = str(DVF_CSV_PATH)) -> pd.DataFrame:
    """
    Charge le fichier DVF brut filtré sur 2024-2025 pour les graphes de tendance.

    Retourne un DataFrame avec au minimum :
        date_mutation, type_local, valeur_fonciere, surface_reelle_bati,
        prix_m2, nature_mutation.

    En cas d'erreur (fichier absent, colonnes manquantes), retourne un DataFrame vide.
    """
    try:
        df = pd.read_csv(dvf_csv_path)
        for col in ("valeur_fonciere", "surface_reelle_bati"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
        df = df[df["date_mutation"] >= "2024-01-01"].copy()
        df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]
        return df
    except Exception:
        return pd.DataFrame()


# ── Modèles DVF dynamiques ────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_dvf_models(dvf_csv_path: str = str(DVF_CSV_PATH)) -> dict:
    """
    Calcule dynamiquement les modèles OLS depuis dvf_toulon.csv.

    Applique les filtres prix/m² définis dans DVF_PM2_FILTERS pour éliminer
    les outliers et obtenir un R² cohérent avec les analyses locales (~0.67).

    Retourne un dict au format :
        {"Appartement": {"slope": …, "intercept": …, "r2": …, "n": …}, …}

    En cas d'erreur (fichier absent, trop peu de données), retourne DVF_REGRESSION
    (valeurs de repli définies dans config.py).
    """
    try:
        df = pd.read_csv(dvf_csv_path)

        # Nettoyage minimal
        for col in ("valeur_fonciere", "surface_reelle_bati"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Filtre temporel : 2 dernières années (2024-2025) uniquement
        if "date_mutation" in df.columns:
            df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
            df = df[df["date_mutation"] >= "2024-01-01"].copy()

        df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]

        models: dict = {}
        for ttype, (lo, hi) in DVF_PM2_FILTERS.items():
            sub = df[
                (df["type_local"] == ttype)
                & (df["nature_mutation"] == "Vente")
                & (df["surface_reelle_bati"] > 10)
                & (df["prix_m2"] >= lo)
                & (df["prix_m2"] <= hi)
            ].dropna(subset=["surface_reelle_bati", "valeur_fonciere"])

            if len(sub) < 10:
                # Pas assez de données → repli sur la valeur statique
                models[ttype] = DVF_REGRESSION.get(ttype, {})
                continue

            x = sub["surface_reelle_bati"].tolist()
            y = sub["valeur_fonciere"].tolist()
            slope, intercept = least_squares_fit(x, y)
            r2 = r_squared(x, y, slope, intercept)

            models[ttype] = {
                "slope":     round(slope, 1),
                "intercept": round(intercept, 1),
                "r2":        round(r2, 3),
                "n":         len(sub),
            }

        return models

    except Exception:
        return DVF_REGRESSION
