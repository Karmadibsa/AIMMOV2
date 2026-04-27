"""
Fonctions statistiques from scratch — V2 NidBuyer.
Portage de AImmoV1/analysis/stats.py.

Référence : Joel Grus, "Data Science From Scratch", ch. 5.
Contrainte : pur Python standard (math, itertools). Zéro numpy/pandas/statistics.

Changement V2 : les fonctions opèrent sur des listes de float déjà extraites
des dicts Supabase (pas de lecture de CSV ici).
Les valeurs None sont filtrées par les helpers extract_* dans engine.py.
"""

import math


# ── Algèbre vectorielle ────────────────────────────────────────────────────────

def dot(v: list[float], w: list[float]) -> float:
    """Produit scalaire Σ(v_i × w_i)."""
    return sum(v_i * w_i for v_i, w_i in zip(v, w))


# ── Moyenne ───────────────────────────────────────────────────────────────────

def mean(xs: list[float]) -> float:
    """Moyenne arithmétique (Σ x_i) / n. Lève ValueError si xs est vide."""
    if not xs:
        raise ValueError("mean() requiert une liste non vide.")
    return sum(xs) / len(xs)


# ── Médiane ───────────────────────────────────────────────────────────────────

def _median_odd(xs: list[float]) -> float:
    return sorted(xs)[len(xs) // 2]


def _median_even(xs: list[float]) -> float:
    s = sorted(xs)
    mid = len(xs) // 2
    return (s[mid - 1] + s[mid]) / 2


def median(xs: list[float]) -> float:
    """Médiane d'une liste non vide."""
    if not xs:
        raise ValueError("median() requiert une liste non vide.")
    return _median_even(xs) if len(xs) % 2 == 0 else _median_odd(xs)


# ── Variance & écart-type ─────────────────────────────────────────────────────

def de_mean(xs: list[float]) -> list[float]:
    """Centre la série : retourne [x_i − x̄ for x_i in xs]."""
    x_bar = mean(xs)
    return [x - x_bar for x in xs]


def variance(xs: list[float]) -> float:
    """
    Variance population : Σ(x_i − x̄)² / n.
    Requiert au moins 2 éléments.
    """
    if len(xs) < 2:
        raise ValueError("variance() requiert au moins 2 éléments.")
    deviations = de_mean(xs)
    return sum(d ** 2 for d in deviations) / len(xs)


def standard_deviation(xs: list[float]) -> float:
    """Écart-type population : √variance(xs)."""
    return math.sqrt(variance(xs))


# ── Covariance & corrélation ──────────────────────────────────────────────────

def covariance(xs: list[float], ys: list[float]) -> float:
    """
    Covariance population : Σ(x_i − x̄)(y_i − ȳ) / n.
    Les deux listes doivent avoir la même longueur.
    """
    if len(xs) != len(ys):
        raise ValueError("covariance() : xs et ys doivent être de même taille.")
    if len(xs) < 2:
        raise ValueError("covariance() requiert au moins 2 paires.")
    return dot(de_mean(xs), de_mean(ys)) / len(xs)


def correlation(xs: list[float], ys: list[float]) -> float:
    """
    Coefficient de Pearson : cov(xs, ys) / (σ_xs × σ_ys).
    Retourne 0.0 si l'une des séries est constante (σ = 0).
    """
    sx = standard_deviation(xs)
    sy = standard_deviation(ys)
    if sx > 0 and sy > 0:
        return covariance(xs, ys) / sx / sy
    return 0.0
