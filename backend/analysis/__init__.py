# backend/analysis/__init__.py
# Expose les fonctions clés pour un import propre depuis le backend.

from .stats import mean, median, standard_deviation, correlation, covariance
from .regression import least_squares_fit, predict, r_squared
from .scoring import (
    stats_marche,
    score_opportunity,
    score_opportunite,
    classify,
    is_opportunity,
    top_opportunities,
    fiche_decision,
    rendement_locatif,
)

__all__ = [
    "mean", "median", "standard_deviation", "correlation", "covariance",
    "least_squares_fit", "predict", "r_squared",
    "stats_marche",
    "score_opportunity", "score_opportunite",
    "classify", "is_opportunity", "top_opportunities",
    "fiche_decision", "rendement_locatif",
]
