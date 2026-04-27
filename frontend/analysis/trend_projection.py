"""
Projection temporelle des prix immobiliers from scratch.
Reference : application de Joel Grus "Data Science From Scratch" ch.14
à une variable temporelle (mois en X, prix médian au m² en Y).

IMPORTANT : pur Python (listes, boucles) — pas de numpy, pandas ni statistics.
"""

from analysis.stats import mean, standard_deviation
from analysis.regression import least_squares_fit, predict


def _period_to_index(period_str: str) -> float:
    """
    Convertit une période "YYYY-MM" en indice numérique continu.

    Formule : (année - 2024) × 12 + mois
    Exemple : "2024-01" → 1.0,  "2025-06" → 18.0

    Args:
        period_str (str): Période au format "YYYY-MM".

    Returns:
        float: Indice numérique (1 = janvier 2024).
    """
    year, month = int(period_str[:4]), int(period_str[5:7])
    return float((year - 2024) * 12 + month)


def _index_to_period(index: float) -> str:
    """
    Convertit un indice numérique en période "YYYY-MM".

    Args:
        index (float): Indice numérique (1 = janvier 2024).

    Returns:
        str: Période au format "YYYY-MM".
    """
    idx = int(round(index))
    year = 2024 + (idx - 1) // 12
    month = ((idx - 1) % 12) + 1
    return f"{year}-{month:02d}"


def compute_trend(
    monthly_prices: dict[str, float],
) -> tuple[float, float]:
    """
    Calcule la régression linéaire prix/m² médian ~ temps (from scratch).

    Args:
        monthly_prices (dict[str, float]): Dictionnaire {période: prix_médian_m²}.
            Clés au format "YYYY-MM", valeurs en €/m².

    Returns:
        tuple[float, float]: (alpha, beta) — ordonnée à l'origine et pente mensuelle.
            beta > 0 = hausse des prix, beta < 0 = baisse.
    """
    if len(monthly_prices) < 2:
        raise ValueError("Au moins 2 périodes sont nécessaires pour calculer la tendance.")

    x = [_period_to_index(p) for p in sorted(monthly_prices.keys())]
    y = [monthly_prices[p] for p in sorted(monthly_prices.keys())]
    return least_squares_fit(x, y)


def project_prices(
    monthly_prices: dict[str, float],
    n_months_ahead: int = 6,
) -> dict[str, dict]:
    """
    Projette les prix immobiliers sur les prochains mois via régression linéaire.

    Construit le modèle sur les données historiques, puis extrapole.
    From scratch — utilise least_squares_fit de analysis.regression.

    Args:
        monthly_prices (dict[str, float]): Historique {période: prix_médian_m²}.
        n_months_ahead (int): Nombre de mois à projeter (défaut : 6).

    Returns:
        dict[str, dict]: Dictionnaire contenant :
            "historique" : {période: prix_observé}
            "projection"  : {période: prix_projeté}
            "alpha"       : float — ordonnée à l'origine
            "beta"        : float — pente (€/m²/mois)
            "tendance"    : str — "hausse" | "baisse" | "stable"
            "variation_annuelle_pct" : float — variation projetée sur 12 mois en %
    """
    if len(monthly_prices) < 2:
        return {"historique": monthly_prices, "projection": {}, "alpha": 0.0,
                "beta": 0.0, "tendance": "stable", "variation_annuelle_pct": 0.0}

    alpha, beta = compute_trend(monthly_prices)

    # Dernier mois connu
    last_period = max(monthly_prices.keys())
    last_index  = _period_to_index(last_period)

    # Projection
    projection: dict[str, float] = {}
    for i in range(1, n_months_ahead + 1):
        future_idx    = last_index + i
        future_period = _index_to_period(future_idx)
        projected_pm2 = round(predict(alpha, beta, future_idx), 0)
        projection[future_period] = max(0.0, projected_pm2)  # prix jamais négatif

    # Tendance qualitative
    variation_annuelle_pct = round(beta * 12 / (alpha + beta * last_index) * 100, 1) if (alpha + beta * last_index) > 0 else 0.0
    if beta > 5:
        tendance = "hausse"
    elif beta < -5:
        tendance = "baisse"
    else:
        tendance = "stable"

    return {
        "historique":              monthly_prices,
        "projection":              projection,
        "alpha":                   round(alpha, 2),
        "beta":                    round(beta, 2),
        "tendance":                tendance,
        "variation_annuelle_pct":  variation_annuelle_pct,
    }
