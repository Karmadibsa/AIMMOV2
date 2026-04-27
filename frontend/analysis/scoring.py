"""
Scoring et classification des opportunités immobilières from scratch.
Reference : logique métier NidDouillet / Observatoire Toulon.

IMPORTANT : pur Python (listes, boucles) — pas de numpy, pandas ni statistics.
"""


def score_opportunity(prix: float, prix_predit: float) -> float:
    """
    Calcule l'écart en % entre le prix réel et le prix prédit par la régression.

    Formule : (prix - prix_predit) / prix_predit × 100

    Un résultat négatif indique un bien sous-évalué (opportunité d'achat).
    Un résultat positif indique un bien sur-évalué.

    Args:
        prix (float): Prix réel du bien (€).
        prix_predit (float): Prix prédit par le modèle de régression (€).

    Returns:
        float: Écart en pourcentage (arrondi à 2 décimales).

    Raises:
        ValueError: si prix_predit est nul ou négatif.
    """
    if prix_predit <= 0:
        raise ValueError(f"prix_predit doit être > 0, reçu : {prix_predit}")
    return round((prix - prix_predit) / prix_predit * 100, 2)


def classify(ecart_pct: float) -> str:
    """
    Classifie un bien selon son écart au prix du marché.

    Seuils appliqués :
        ecart_pct < -10 %   → "Opportunité"
        -10 % ≤ ecart_pct < -5 % → "Bonne affaire"
        -5 % ≤ ecart_pct ≤ +5 % → "Prix marché"
        ecart_pct > +5 %    → "Prix élevé"

    Args:
        ecart_pct (float): Écart au prix du marché en %.

    Returns:
        str: Catégorie parmi "Opportunité", "Bonne affaire", "Prix marché", "Prix élevé".
    """
    if ecart_pct < -10:
        return "Opportunité"
    elif ecart_pct < -5:
        return "Bonne affaire"
    elif ecart_pct <= 5:
        return "Prix marché"
    else:
        return "Prix élevé"


def is_opportunity(ecart_pct: float, seuil: float = -10.0) -> bool:
    """
    Indique si un bien est une opportunité d'achat selon le seuil donné.

    Args:
        ecart_pct (float): Écart au prix du marché en %.
        seuil (float): Seuil de détection (défaut : -10.0 %).

    Returns:
        bool: True si ecart_pct < seuil (bien sous-évalué).
    """
    return ecart_pct < seuil


def top_opportunities(
    items: list[dict],
    ecart_col: str = "ecart_pct",
    seuil: float = -10.0,
    n: int = 10,
) -> list[dict]:
    """
    Filtre et trie une liste de biens pour retourner les meilleures opportunités.
    From scratch — sans pandas ni numpy.

    Args:
        items (list[dict]): Liste de dictionnaires représentant des biens.
        ecart_col (str): Nom de la clé contenant l'écart en % (défaut : "ecart_pct").
        seuil (float): Seuil de détection (défaut : -10.0 %).
        n (int): Nombre maximum d'opportunités à retourner (défaut : 10).

    Returns:
        list[dict]: Liste des n meilleures opportunités triées par écart croissant.
    """
    opps = [
        item for item in items
        if item.get(ecart_col) is not None and item[ecart_col] < seuil
    ]
    return sorted(opps, key=lambda x: x[ecart_col])[:n]
