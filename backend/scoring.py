"""
Calcul du score d'opportunité d'un bien immobilier.
Compare le prix au m² du bien à la médiane DVF du quartier.
"""

MALUS_TRAVAUX = {
    "investissement": 0.0,   # travaux = opportunité de négociation
    "rp":             0.3,   # travaux = contrainte forte pour une famille
    "rs":             0.15,
    "mixte":          0.1,
}


def score_opportunite(
    bien: dict,
    mediane_quartier: float,
    profil: str,
    vision_result: dict | None = None,
) -> dict:
    """
    Calcule le score d'opportunité d'un bien vs la médiane du quartier.

    Score signé : positif = bien sous-évalué, négatif = sur-évalué.
    Formule : score = -ecart_pct × 2  (ex : -7 % → +14, +21 % → -42).

    Args:
        bien:             dict avec 'prix' et 'surface'.
        mediane_quartier: médiane DVF du quartier en €/m².
        profil:           "rp" | "rs" | "investissement" | "mixte".
        vision_result:    dict optionnel ; reconnaît les clés 'travaux' (bool)
                          et 'travaux_score' (float 0-1 > 0.5 = travaux détectés).

    Returns:
        dict : prix_m2, ecart_pct, label, score, opportunite.
    """
    try:
        prix    = float(bien["prix"])
        surface = float(bien["surface"])
    except (KeyError, TypeError, ValueError):
        return {
            "prix_m2": None, "ecart_pct": None,
            "label": "Données insuffisantes", "score": None, "opportunite": False,
        }

    if surface <= 0 or not mediane_quartier or mediane_quartier <= 0:
        return {
            "prix_m2": None, "ecart_pct": None,
            "label": "Données insuffisantes", "score": None, "opportunite": False,
        }

    prix_m2   = prix / surface
    ecart_pct = round((prix_m2 - mediane_quartier) / mediane_quartier * 100, 2)

    if ecart_pct < -10:
        label = "Opportunité"
    elif ecart_pct < -5:
        label = "Bonne affaire"
    elif ecart_pct <= 5:
        label = "Prix marché"
    else:
        label = "Prix élevé"

    # Score signé : bien sous-évalué → positif, sur-évalué → négatif
    score = round(-ecart_pct * 2, 2)

    # Malus travaux — réduit le score pour les profils contraints
    has_travaux = bool(
        vision_result and (
            vision_result.get("travaux")
            or vision_result.get("travaux_score", 0) > 0.5
        )
    )
    if has_travaux and score > 0:
        malus = MALUS_TRAVAUX.get(profil, 0.0)
        score = round(score * (1.0 - malus), 2)

    return {
        "prix_m2":     round(prix_m2, 2),
        "ecart_pct":   ecart_pct,
        "label":       label,
        "score":       score,
        "opportunite": ecart_pct < -10,
    }


def fiche_decision(bien: dict, dvf_quartier: dict) -> str:
    """
    Génère la fiche structurée transmise au LLM.

    dvf_quartier accepte les clés 'mediane_m2' ou 'mediane_prix_m2'.

    Returns:
        Texte structuré : prix vs médiane, écart %, conseil de négociation.
    """
    titre      = bien.get("titre", "Bien sans titre")
    quartier   = bien.get("quartier", "Quartier inconnu")
    mediane_m2 = (
        dvf_quartier.get("mediane_m2")
        or dvf_quartier.get("mediane_prix_m2")
    )

    try:
        prix    = float(bien["prix"])
        surface = float(bien["surface"])
        mediane = float(mediane_m2)
    except (KeyError, TypeError, ValueError):
        return (
            f"FICHE BIEN : {titre}\n"
            f"  Quartier : {quartier}\n"
            "  ⚠ Données insuffisantes pour calculer l'écart marché.\n"
        )

    if surface <= 0 or mediane <= 0:
        return (
            f"FICHE BIEN : {titre}\n"
            f"  Quartier : {quartier}\n"
            "  ⚠ Surface ou médiane nulle.\n"
        )

    prix_m2   = prix / surface
    ecart_pct = (prix_m2 - mediane) / mediane * 100
    conseil   = (
        "Bonne marge de négociation envisageable."
        if ecart_pct < -5
        else "Prix aligné ou supérieur au marché — négocier avec prudence."
    )

    return (
        f"FICHE BIEN : {titre}\n"
        f"  Quartier         : {quartier}\n"
        f"  Prix             : {prix:,.0f} € ({surface:.0f} m²)\n"
        f"  Prix/m²          : {prix_m2:.0f} €/m²\n"
        f"  Médiane quartier : {mediane:.0f} €/m²\n"
        f"  Écart marché     : {ecart_pct:+.1f} %\n"
        f"  Conseil          : {conseil}\n"
    )


def rendement_locatif(bien: dict, loyer_estime: float) -> dict:
    """
    Calcule le rendement brut et net estimé.

    Returns:
        dict avec 'rendement_brut_pct', 'rendement_net_pct'.
    """
    try:
        prix         = float(bien["prix"])
        loyer_annuel = float(loyer_estime) * 12
    except (KeyError, TypeError, ValueError):
        return {"rendement_brut_pct": None, "rendement_net_pct": None}

    if prix <= 0 or loyer_estime <= 0:
        return {"rendement_brut_pct": None, "rendement_net_pct": None}

    brut = loyer_annuel / prix * 100
    net  = brut * 0.75  # 25 % de charges (taxe foncière + entretien + gestion)

    return {
        "rendement_brut_pct": round(brut, 2),
        "rendement_net_pct":  round(net, 2),
    }
