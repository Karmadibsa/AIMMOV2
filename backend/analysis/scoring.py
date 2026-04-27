"""
Scoring et opportunités immobilières from scratch — V2 NidBuyer.
Portage ET extension de AImmoV1/analysis/scoring.py.

Contrainte absolue : pur Python standard (math, itertools, os).
Zéro numpy / pandas / sklearn.

Source de données V2 :
  Les fonctions publiques acceptent deux modes d'appel :
    (A) annonces=[...] fourni directement → mode "données déjà chargées"
        (utilisé par les routes FastAPI qui ont déjà fait leur requête Supabase)
    (B) annonces=None + supabase_client fourni → la fonction interroge
        elle-même la table "annonces" et applique les filtres demandés.

  Le module ne lit JAMAIS de CSV.
"""

import logging
import math
import os
from pathlib import Path
from typing import TYPE_CHECKING

from .stats import mean, median, standard_deviation
from .regression import least_squares_fit, predict, r_squared

if TYPE_CHECKING:
    # Import uniquement pour le typage, pas au runtime — évite la dépendance
    # circulaire si supabase n'est pas installé en mode test.
    from supabase import Client

logger = logging.getLogger(__name__)

# ── Constantes métier ─────────────────────────────────────────────────────────

MALUS_TRAVAUX: dict[str, float] = {
    "investissement": 0.0,   # travaux = levier de négociation
    "rp":             0.3,   # résidence principale : contrainte forte
    "rs":             0.15,
    "mixte":          0.1,
}

# Part des charges sur le loyer brut annuel (taxe foncière + entretien + gestion)
CHARGES_NETTES_PCT = 0.25


# ── Récupération Supabase ─────────────────────────────────────────────────────

# Colonnes nécessaires pour l'analyse — on ne sélectionne que ce dont on a besoin
_COLONNES_ANALYSE = (
    "id, source, type_local, titre, "
    "prix, surface, pieces, quartier, lien"
)


def _charger_depuis_supabase(
    supabase_client: "Client",
    commune: str | None = None,
    type_local: str | None = None,
    page_size: int = 1000,
) -> list[dict]:
    """
    Récupère les annonces de la table Supabase avec pagination automatique.

    Args:
        supabase_client: instance supabase.Client déjà créée.
        commune:         filtre optionnel sur quartier (ex: "Mourillon").
        type_local:      filtre optionnel sur type_local (ex: "Appartement").
        page_size:       nombre de lignes par appel (max Supabase = 1 000).

    Returns:
        Liste brute de dicts tels que retournés par l'API Supabase.
    """
    annonces: list[dict] = []
    offset = 0

    while True:
        query = (
            supabase_client.table("annonces")
            .select(_COLONNES_ANALYSE)
        )
        if commune:
            query = query.eq("quartier", commune)
        if type_local:
            query = query.eq("type_local", type_local)

        response = query.range(offset, offset + page_size - 1).execute()
        batch = response.data

        if not batch:
            break

        annonces.extend(batch)

        if len(batch) < page_size:
            break   # Dernier lot partiel → fin de table

        offset += page_size

    logger.info(f"_charger_depuis_supabase() : {len(annonces)} annonces chargées.")
    return annonces


# ── Helpers d'extraction (from scratch) ──────────────────────────────────────

def _extract_pairs(
    annonces: list[dict], key_x: str, key_y: str
) -> tuple[list[float], list[float]]:
    """
    Extrait deux séries numériques depuis une liste de dicts.
    Seules les lignes où les DEUX champs sont valides (non-None, non-NaN) sont conservées.
    """
    xs, ys = [], []
    for a in annonces:
        vx = a.get(key_x)
        vy = a.get(key_y)
        if vx is None or vy is None:
            continue
        try:
            fx, fy = float(vx), float(vy)
            if not math.isnan(fx) and not math.isnan(fy) and fx > 0 and fy > 0:
                xs.append(fx)
                ys.append(fy)
        except (TypeError, ValueError):
            continue
    return xs, ys


def _to_float(val) -> float | None:
    """Convertit une valeur en float ; retourne None si impossible."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


# ── Analyse de marché ─────────────────────────────────────────────────────────

def stats_marche(
    annonces: list[dict] | None = None,
    *,
    supabase_client: "Client | None" = None,
    commune: str | None = None,
    type_local: str | None = None,
) -> dict:
    """
    Calcule les indicateurs statistiques du marché (from scratch).

    Modes d'appel :
        stats_marche(annonces=[...])                       # données déjà chargées
        stats_marche(supabase_client=sb, commune="Toulon") # charge depuis Supabase

    Args:
        annonces:        liste de dicts Supabase (optionnel si supabase_client fourni).
        supabase_client: client Supabase (optionnel si annonces fourni).
        commune:         filtre géographique (ignoré si annonces fourni).
        type_local:      filtre type de bien (ignoré si annonces fourni).

    Returns:
        dict avec : n_annonces, prix_moyen, prix_median, prix_min, prix_max,
                    surface_moyenne, surface_mediane, ecart_type_prix,
                    prix_m2_moyen, prix_m2_median,
                    regression_alpha, regression_beta, r2.
        Retourne {} si données insuffisantes.

    Raises:
        ValueError: si ni annonces ni supabase_client ne sont fournis.
    """
    if annonces is None:
        if supabase_client is None:
            raise ValueError(
                "Fournir soit annonces=[...] soit supabase_client=<Client>."
            )
        annonces = _charger_depuis_supabase(supabase_client, commune, type_local)

    surfaces, prix = _extract_pairs(annonces, "surface", "prix")

    if len(prix) < 2:
        logger.warning("stats_marche() : moins de 2 annonces valides, impossible de calculer.")
        return {}

    prix_m2 = [p / s for p, s in zip(prix, surfaces)]  # s > 0 garanti par _extract_pairs

    result: dict = {
        "n_annonces":      len(prix),
        "prix_moyen":      round(mean(prix), 2),
        "prix_median":     round(median(prix), 2),
        "prix_min":        round(min(prix), 2),
        "prix_max":        round(max(prix), 2),
        "surface_moyenne": round(mean(surfaces), 2),
        "surface_mediane": round(median(surfaces), 2),
        "ecart_type_prix": round(standard_deviation(prix), 2),
        "prix_m2_moyen":   round(mean(prix_m2), 2),
        "prix_m2_median":  round(median(prix_m2), 2),
    }

    try:
        alpha, beta = least_squares_fit(surfaces, prix)
        result["regression_alpha"] = round(alpha, 2)
        result["regression_beta"]  = round(beta, 2)
        result["r2"]               = round(r_squared(alpha, beta, surfaces, prix), 4)
    except ValueError as e:
        logger.warning(f"stats_marche() : régression impossible — {e}")

    return result


def mediane_prix_m2(
    annonces: list[dict] | None = None,
    *,
    supabase_client: "Client | None" = None,
    commune: str | None = None,
    type_local: str | None = None,
) -> float | None:
    """
    Retourne uniquement la médiane du prix au m² pour un segment de marché.
    Utilisé par score_opportunite() pour comparer un bien au marché local.
    """
    stats = stats_marche(
        annonces,
        supabase_client=supabase_client,
        commune=commune,
        type_local=type_local,
    )
    return stats.get("prix_m2_median")


# ── Scoring élémentaire (V1 conservé à l'identique) ──────────────────────────

def score_opportunity(prix: float, prix_predit: float) -> float:
    """
    Écart en % entre prix réel et prix prédit par la régression.
    Formule : (prix − prix_predit) / prix_predit × 100.
    Résultat négatif = bien sous-évalué (opportunité d'achat).
    """
    if prix_predit <= 0:
        raise ValueError(f"prix_predit doit être > 0, reçu : {prix_predit}")
    return round((prix - prix_predit) / prix_predit * 100, 2)


def classify(ecart_pct: float) -> str:
    """
    Classifie un bien selon son écart au prix du marché.
        < -10 %          → "Opportunité"
        [-10 %, -5 [     → "Bonne affaire"
        [-5 %, +5 %]     → "Prix marché"
        > +5 %           → "Prix élevé"
    """
    if ecart_pct < -10:
        return "Opportunité"
    if ecart_pct < -5:
        return "Bonne affaire"
    if ecart_pct <= 5:
        return "Prix marché"
    return "Prix élevé"


def is_opportunity(ecart_pct: float, seuil: float = -10.0) -> bool:
    """True si le bien est sous-évalué au-delà du seuil."""
    return ecart_pct < seuil


def top_opportunities(
    items: list[dict],
    ecart_col: str = "ecart_pct",
    seuil: float = -10.0,
    n: int = 10,
) -> list[dict]:
    """
    Filtre les items sous le seuil et retourne les n meilleurs, triés
    par écart croissant (le plus sous-évalué en premier).
    Ignore silencieusement les items où ecart_col est None.
    """
    opps = [
        item for item in items
        if item.get(ecart_col) is not None and item[ecart_col] < seuil
    ]
    return sorted(opps, key=lambda x: x[ecart_col])[:n]


# ── Score d'opportunité complet (profil acheteur + vision IA) ─────────────────

def score_opportunite(
    bien: dict,
    mediane_quartier: float,
    profil: str,
    vision_result: dict | None = None,
) -> dict:
    """
    Score d'opportunité d'un bien vs la médiane du quartier.

    Args:
        bien:             dict Supabase avec 'prix' et
                          'surface' (peuvent être None).
        mediane_quartier: médiane DVF du quartier en €/m² (float > 0).
        profil:           "rp" | "rs" | "investissement" | "mixte".
        vision_result:    dict optionnel issu de l'analyse photo IA.
                          Si {"travaux": True}, applique le malus du profil.

    Returns:
        dict : prix_m2, ecart_pct, label, score (0-100), opportunite (bool).
               Les champs numériques sont None si données insuffisantes.
    """
    prix    = _to_float(bien.get("prix"))
    surface = _to_float(bien.get("surface"))

    if prix is None or surface is None or surface <= 0 or mediane_quartier <= 0:
        return {
            "prix_m2":     None,
            "ecart_pct":   None,
            "label":       "Données insuffisantes",
            "score":       None,
            "opportunite": False,
        }

    prix_m2   = prix / surface
    ecart_pct = round((prix_m2 - mediane_quartier) / mediane_quartier * 100, 2)
    label     = classify(ecart_pct)

    # Score brut linéaire : 100 si écart ≤ -20 %, 0 si écart ≥ +20 %
    score_brut = max(0.0, min(100.0, (20.0 - ecart_pct) / 40.0 * 100.0))

    # Malus travaux si signal IA
    malus = MALUS_TRAVAUX.get(profil, 0.0)
    if vision_result and vision_result.get("travaux"):
        score_final = round(score_brut * (1.0 - malus), 2)
    else:
        score_final = round(score_brut, 2)

    return {
        "prix_m2":     round(prix_m2, 2),
        "ecart_pct":   ecart_pct,
        "label":       label,
        "score":       score_final,
        "opportunite": is_opportunity(ecart_pct),
    }


# ── Fiche décision (contexte LLM) ─────────────────────────────────────────────

def fiche_decision(bien: dict, dvf_quartier: dict) -> str:
    """
    Génère la fiche structurée transmise au LLM pour argumenter sa réponse.

    Args:
        bien:          dict Supabase de l'annonce.
        dvf_quartier:  dict avec 'mediane_m2' (float) et 'quartier' (str).

    Returns:
        Texte structuré multi-lignes.
    """
    titre        = bien.get("titre", "Bien sans titre")
    prix         = _to_float(bien.get("prix"))
    surface      = _to_float(bien.get("surface"))
    commune      = bien.get("quartier", "Inconnue")
    mediane_m2   = _to_float(dvf_quartier.get("mediane_m2"))
    quartier_nom = dvf_quartier.get("quartier", "quartier inconnu")

    if prix is None or surface is None or surface <= 0 or mediane_m2 is None or mediane_m2 <= 0:
        return (
            f"FICHE BIEN : {titre}\n"
            f"  Commune : {commune}\n"
            f"  ⚠ Données insuffisantes pour calculer l'écart marché.\n"
        )

    prix_m2   = prix / surface
    ecart_pct = (prix_m2 - mediane_m2) / mediane_m2 * 100
    label     = classify(ecart_pct)
    conseil   = (
        "Bonne marge de négociation envisageable."
        if ecart_pct < -5
        else "Prix aligné ou supérieur au marché — négocier avec prudence."
    )

    return (
        f"FICHE BIEN : {titre}\n"
        f"  Commune         : {commune}\n"
        f"  Prix            : {prix:,.0f} €  ({surface} m²)\n"
        f"  Prix/m²         : {prix_m2:.0f} €/m²\n"
        f"  Médiane {quartier_nom} : {mediane_m2:.0f} €/m²\n"
        f"  Écart marché    : {ecart_pct:+.1f} %  → {label}\n"
        f"  Conseil         : {conseil}\n"
    )


# ── Rendement locatif ─────────────────────────────────────────────────────────

def rendement_locatif(bien: dict, loyer_estime: float) -> dict:
    """
    Calcule le rendement brut et net estimé.

    Args:
        bien:         dict Supabase avec 'prix'.
        loyer_estime: loyer mensuel estimé en €.

    Returns:
        dict : rendement_brut_pct, rendement_net_pct (None si données invalides).
    """
    prix = _to_float(bien.get("prix"))

    if prix is None or prix <= 0 or loyer_estime <= 0:
        return {"rendement_brut_pct": None, "rendement_net_pct": None}

    loyer_annuel = loyer_estime * 12
    brut         = loyer_annuel / prix * 100
    net          = (loyer_annuel * (1 - CHARGES_NETTES_PCT)) / prix * 100

    return {
        "rendement_brut_pct": round(brut, 2),
        "rendement_net_pct":  round(net, 2),
    }
