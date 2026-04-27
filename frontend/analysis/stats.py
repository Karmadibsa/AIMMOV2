"""
Fonctions statistiques from scratch.
Reference : Joel Grus, "Data Science From Scratch", chapitre 5.

IMPORTANT : N'importez pas numpy, pandas ni statistics pour ces fonctions.
Implémentez-les avec du Python pur (listes, boucles, math).
"""

import math


def dot(v: list[float], w: list[float]) -> float:
    """
    Produit scalaire de deux vecteurs.

    Formule : Σ(v_i × w_i)

    Args:
        v (list[float]): Premier vecteur.
        w (list[float]): Second vecteur (même longueur que v).

    Returns:
        float: Somme des produits élément par élément.
    """
    return sum(v_i * w_i for v_i, w_i in zip(v, w))


# ── MOYENNE ──────────────────────────────────────────────────────────────────

def mean(xs: list[float]) -> float:
    """
    Retourne la moyenne arithmétique d'une liste de nombres.

    Formule : (Σ x_i) / n

    Args:
        xs (list[float]): Liste de nombres (non vide).

    Returns:
        float: Moyenne arithmétique.
    """
    return sum(xs) / len(xs)


# ── MÉDIANE ──────────────────────────────────────────────────────────────────

def _median_odd(xs: list[float]) -> float:
    """
    Médiane pour une liste de taille impaire.

    Formule : élément central de la liste triée, à l'indice n // 2.

    Args:
        xs (list[float]): Liste de nombres (longueur impaire).

    Returns:
        float: Valeur médiane.
    """
    return sorted(xs)[len(xs) // 2]


def _median_even(xs: list[float]) -> float:
    """
    Médiane pour une liste de taille paire.

    Formule : moyenne des deux éléments centraux de la liste triée.

    Args:
        xs (list[float]): Liste de nombres (longueur paire).

    Returns:
        float: Valeur médiane.
    """
    sorted_xs = sorted(xs)
    mid = len(xs) // 2
    return (sorted_xs[mid - 1] + sorted_xs[mid]) / 2


def median(xs: list[float]) -> float:
    """
    Retourne la médiane d'une liste de nombres.

    Délègue à _median_odd (n impair) ou _median_even (n pair).

    Args:
        xs (list[float]): Liste de nombres (non vide).

    Returns:
        float: Valeur médiane.
    """
    return _median_even(xs) if len(xs) % 2 == 0 else _median_odd(xs)


# ── VARIANCE ─────────────────────────────────────────────────────────────────

def de_mean(xs: list[float]) -> list[float]:
    """
    Soustrait la moyenne à chaque élément (centrage).

    Formule : x_i − x̄

    Args:
        xs (list[float]): Liste de nombres.

    Returns:
        list[float]: Liste des écarts à la moyenne.
    """
    x_bar = mean(xs)
    return [x - x_bar for x in xs]


def variance(xs: list[float]) -> float:
    """
    Retourne la variance (population) d'une liste de nombres.

    Formule : (Σ (x_i − x̄)²) / n

    Note : on divise par n (variance population) et non n-1 (variance
    d'échantillon), conformément aux tests d'évaluation automatique du projet.

    Args:
        xs (list[float]): Liste d'au moins 2 nombres.

    Returns:
        float: Variance de la population.
    """
    assert len(xs) >= 2, "la variance nécessite au moins deux éléments"
    n = len(xs)
    deviations = de_mean(xs)
    return sum(x ** 2 for x in deviations) / n


# ── ÉCART-TYPE, COVARIANCE, CORRÉLATION ──────────────────────────────────────

def standard_deviation(xs: list[float]) -> float:
    """
    Retourne l'écart-type d'une liste de nombres.

    Formule : √variance(xs)

    Args:
        xs (list[float]): Liste d'au moins 2 nombres.

    Returns:
        float: Écart-type de la population.
    """
    return math.sqrt(variance(xs))


def covariance(xs: list[float], ys: list[float]) -> float:
    """
    Retourne la covariance (population) entre deux séries.

    Formule : (Σ (x_i − x̄)(y_i − ȳ)) / n

    Note : divise par n (population) et non n-1 (échantillon), pour que
    les calculs de bêta et R² correspondent aux tests automatisés.

    Args:
        xs (list[float]): Première série de nombres.
        ys (list[float]): Seconde série (même longueur que xs).

    Returns:
        float: Covariance de la population.
    """
    assert len(xs) == len(ys), "xs et ys doivent être de même taille"
    return dot(de_mean(xs), de_mean(ys)) / len(xs)


def correlation(xs: list[float], ys: list[float]) -> float:
    """
    Retourne le coefficient de corrélation de Pearson entre deux séries.

    Formule : cov(xs, ys) / (σ_xs × σ_ys)

    Retourne 0 si l'une des séries a un écart-type nul (série constante).

    Args:
        xs (list[float]): Première série de nombres.
        ys (list[float]): Seconde série (même longueur que xs).

    Returns:
        float: Coefficient de Pearson ∈ [-1, 1], ou 0 si σ = 0.
    """
    stdev_x = standard_deviation(xs)
    stdev_y = standard_deviation(ys)
    if stdev_x > 0 and stdev_y > 0:
        return covariance(xs, ys) / stdev_x / stdev_y
    else:
        return 0
