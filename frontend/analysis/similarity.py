"""
Moteur de similarité k-NN (k-Nearest Neighbors) from scratch.
Reference : Joel Grus, "Data Science From Scratch", chapitre 12.

Permet de trouver les k biens immobiliers les plus similaires à un bien cible
en calculant la distance euclidienne dans un espace de features normalisées.

IMPORTANT : pur Python (listes, boucles) — pas de numpy, pandas ni sklearn.
"""

import math


# ── Distances ────────────────────────────────────────────────────────────────

def euclidean_distance(a: list[float], b: list[float]) -> float:
    """
    Calcule la distance euclidienne entre deux vecteurs de features.

    Formule : √(Σ (a_i − b_i)²)

    Args:
        a (list[float]): Premier vecteur de features.
        b (list[float]): Second vecteur (même longueur que a).

    Returns:
        float: Distance euclidienne ≥ 0.
    """
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


# ── Normalisation ─────────────────────────────────────────────────────────────

def normalize_features(
    items: list[dict],
    feature_keys: list[str],
) -> tuple[list[list[float]], list[float], list[float]]:
    """
    Normalise les features d'une liste de biens (min-max scaling).

    Formule : x_norm = (x − min) / (max − min)
    Valeur 0.5 si max == min (colonne constante → pas d'information).

    Args:
        items (list[dict]): Liste de dictionnaires représentant des biens.
        feature_keys (list[str]): Liste des clés à utiliser comme features.

    Returns:
        tuple:
            - list[list[float]]  : matrice normalisée (n_items × n_features)
            - list[float]        : valeurs min par feature
            - list[float]        : valeurs max par feature
    """
    n = len(items)
    k = len(feature_keys)

    # Extraction des valeurs brutes (None → 0 par défaut)
    raw: list[list[float]] = []
    for item in items:
        row = []
        for key in feature_keys:
            val = item.get(key)
            row.append(float(val) if val is not None and not _is_nan(val) else 0.0)
        raw.append(row)

    # Min / Max par feature
    mins = [min(raw[i][j] for i in range(n)) for j in range(k)]
    maxs = [max(raw[i][j] for i in range(n)) for j in range(k)]

    # Normalisation
    normed: list[list[float]] = []
    for row in raw:
        norm_row = []
        for j in range(k):
            span = maxs[j] - mins[j]
            norm_row.append((row[j] - mins[j]) / span if span > 0 else 0.5)
        normed.append(norm_row)

    return normed, mins, maxs


def _is_nan(v) -> bool:
    """Retourne True si v est un float NaN."""
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return False


# ── k-NN ─────────────────────────────────────────────────────────────────────

def knn_similar(
    target_idx: int,
    normed_matrix: list[list[float]],
    k: int = 3,
) -> list[tuple[int, float]]:
    """
    Trouve les k voisins les plus proches d'un bien dans l'espace normalisé.

    From scratch — tri par distance euclidienne, pas de sklearn.

    Args:
        target_idx (int): Index du bien cible dans normed_matrix.
        normed_matrix (list[list[float]]): Matrice normalisée (n × m).
        k (int): Nombre de voisins à retourner (défaut : 3).

    Returns:
        list[tuple[int, float]]: Liste de (index, distance) triés par distance
            croissante, sans inclure le bien cible lui-même.
    """
    target = normed_matrix[target_idx]
    distances = []
    for i, vec in enumerate(normed_matrix):
        if i == target_idx:
            continue
        dist = euclidean_distance(target, vec)
        distances.append((i, dist))

    distances.sort(key=lambda x: x[1])
    return distances[:k]


def find_similar_properties(
    items: list[dict],
    target_idx: int,
    feature_keys: list[str] | None = None,
    k: int = 3,
) -> list[dict]:
    """
    Retourne les k biens les plus similaires au bien cible.

    Features utilisées par défaut :
        surface_reelle_bati, valeur_fonciere, nombre_pieces_principales, prix_m2

    Chaque résultat est enrichi d'une clé "_distance" (0 = identique).

    Args:
        items (list[dict]): Liste de biens (dictionnaires).
        target_idx (int): Index du bien cible dans items.
        feature_keys (list[str] | None): Features à utiliser (défaut ci-dessus).
        k (int): Nombre de voisins (défaut : 3).

    Returns:
        list[dict]: Les k biens similaires, enrichis de "_distance".
    """
    if feature_keys is None:
        feature_keys = [
            "surface_reelle_bati",
            "valeur_fonciere",
            "nombre_pieces_principales",
            "prix_m2",
        ]

    # Normalisation
    normed, _, _ = normalize_features(items, feature_keys)

    # k-NN
    neighbors = knn_similar(target_idx, normed, k=k)

    results = []
    for idx, dist in neighbors:
        enriched = dict(items[idx])
        enriched["_distance"] = round(dist, 4)
        enriched["_similarite_pct"] = round(max(0.0, (1 - dist) * 100), 1)
        results.append(enriched)

    return results
