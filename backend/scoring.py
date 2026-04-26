"""
Calcul du score d'opportunité d'un bien immobilier.
Compare le prix au m² du bien à la médiane DVF du quartier.
"""


MALUS_TRAVAUX = {
    "investissement": 0.0,   # travaux = opportunité de négociation
    "rp":             0.3,   # travaux = contrainte pour une famille
    "rs":             0.15,
    "mixte":          0.1,
}


def score_opportunite(bien: dict, mediane_quartier: float, profil: str, vision_result: dict | None = None) -> dict:
    """
    Calcule le score d'opportunité d'un bien.

    Args:
        bien: dict avec au moins 'prix' et 'surface'
        mediane_quartier: médiane DVF du quartier (€/m²)
        profil: "rp" | "rs" | "investissement" | "mixte"
        vision_result: résultat optionnel de l'analyse photo (bonus)

    Returns:
        dict avec 'score', 'ecart_pct', 'label'
    """
    # TODO : calculer prix_m2, écart à la médiane, appliquer malus travaux si vision_result fourni
    raise NotImplementedError


def fiche_decision(bien: dict, dvf_quartier: dict) -> str:
    """
    Génère la fiche structurée transmise au LLM.

    Returns:
        Texte structuré : prix vs médiane, écart %, conseil de négociation
    """
    # TODO : calculer l'écart et retourner une chaîne formatée
    raise NotImplementedError


def rendement_locatif(bien: dict, loyer_estime: float) -> dict:
    """
    Calcule le rendement brut et net estimé (bonus investissement).

    Args:
        bien: dict avec 'prix'
        loyer_estime: loyer mensuel estimé en €

    Returns:
        dict avec 'rendement_brut_pct', 'rendement_net_pct'
    """
    # TODO : rendement brut = loyer_annuel / prix * 100
    raise NotImplementedError
