"""
Régression linéaire simple from scratch — V2 NidBuyer.
Portage de AImmoV1/analysis/regression.py.

Référence : Joel Grus, "Data Science From Scratch", ch. 14.
Contrainte : pur Python standard. Zéro numpy/pandas/sklearn.

Changement V2 : les fonctions reçoivent directement des listes de float.
La préparation des données (extraction depuis dicts Supabase, filtrage None)
est à la charge du moteur d'analyse (engine.py).
"""

import math

from .stats import mean, variance, covariance, correlation, standard_deviation


# ── Prédiction ────────────────────────────────────────────────────────────────

def predict(alpha: float, beta: float, x_i: float) -> float:
    """ŷ = alpha + beta × x_i."""
    return beta * x_i + alpha


# ── Résidu ────────────────────────────────────────────────────────────────────

def error(alpha: float, beta: float, x_i: float, y_i: float) -> float:
    """Résidu = ŷ − y_i (positif = surestimation)."""
    return predict(alpha, beta, x_i) - y_i


# ── Somme des erreurs au carré ────────────────────────────────────────────────

def sum_of_sqerrors(alpha: float, beta: float, x: list[float], y: list[float]) -> float:
    """SS_res = Σ (ŷ_i − y_i)²."""
    return sum(error(alpha, beta, xi, yi) ** 2 for xi, yi in zip(x, y))


# ── Moindres carrés ───────────────────────────────────────────────────────────

def least_squares_fit(x: list[float], y: list[float]) -> tuple[float, float]:
    """
    OLS : calcule (alpha, beta) tel que y ≈ alpha + beta × x.

    Formules :
        beta  = corr(x, y) × σ_y / σ_x
        alpha = ȳ − beta × x̄

    Requiert au moins 2 paires valides (assertion levée sinon).
    """
    if len(x) < 2 or len(y) < 2:
        raise ValueError("least_squares_fit() requiert au moins 2 points.")
    beta = correlation(x, y) * standard_deviation(y) / standard_deviation(x)
    alpha = mean(y) - beta * mean(x)
    return alpha, beta


# ── Coefficient de détermination ──────────────────────────────────────────────

def r_squared(alpha: float, beta: float, x: list, y: list) -> float:
    """
    R² = 1 − SS_res / SS_tot.

    Robuste aux None : filtre automatiquement les paires invalides avant calcul.
    Retourne 0.0 si moins de 2 points valides ou si SS_tot == 0.
    """
    pairs = [
        (xi, yi) for xi, yi in zip(x, y)
        if xi is not None and yi is not None
        and not (isinstance(xi, float) and math.isnan(xi))
        and not (isinstance(yi, float) and math.isnan(yi))
    ]
    if len(pairs) < 2:
        return 0.0

    xc = [p[0] for p in pairs]
    yc = [p[1] for p in pairs]

    ss_res = sum_of_sqerrors(alpha, beta, xc, yc)
    mean_y = mean(yc)
    ss_tot = sum((yi - mean_y) ** 2 for yi in yc)

    if ss_tot == 0:
        return 0.0

    return 1.0 - (ss_res / ss_tot)
