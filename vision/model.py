"""
Interface publique R&D Vision.

evaluer_etat_bien(photos) est l'entrée standardisée qu'utilise le reste du
produit (backend, tests). Elle délègue à l'implémentation choisie (LLM Gemini
sous vision/llm/) et projette le résultat au contrat strict attendu par les
tests :

    {
        "etat_general":       "excellent" | "bon" | "correct" | "a_renover",
        "travaux_detectes":   list[str],
        "estimation_travaux": "0-5k" | "5-20k" | "20-50k" | ">50k",
        "luminosite":         1-5,
        "score_presentation": 1-10,
    }

Des champs additionnels (etat_label, points_forts, points_vigilance,
fourchette_travaux_eur, justification_etat) sont également présents pour les
besoins d'affichage côté UI — les tests utilisent issubset() donc les clés
supplémentaires sont autorisées.
"""

from vision.llm.evaluate import analyser_photos, build_markdown


def evaluer_etat_bien(
    photos: list,
    titre: str | None = None,
    type_bien: str | None = None,
    max_images: int = 4,
) -> dict:
    """
    Analyse les photos d'un bien et retourne une estimation structurée de son état.

    Args:
        photos     : liste de chemins locaux ou d'URLs http(s) vers les photos.
        titre      : titre de l'annonce (contexte optionnel pour le LLM).
        type_bien  : Appartement / Maison / etc. (contexte optionnel).
        max_images : plafond du nombre d'images analysées (coût/latence).

    Returns:
        Dict respectant le contrat de tests/test_vision.py + champs riches pour l'UI.

    Raises:
        ValueError   : photos vide ou sources non chargeables.
        RuntimeError : appel Gemini en échec.
    """
    if not photos:
        raise ValueError("Au moins une photo est requise.")

    return analyser_photos(
        photos=photos,
        titre=titre,
        type_bien=type_bien,
        max_images=max_images,
    )


def evaluer_etat_bien_markdown(parsed: dict) -> str:
    """Helper : reconstruit la fiche markdown depuis un résultat d'evaluer_etat_bien."""
    return build_markdown(parsed)
