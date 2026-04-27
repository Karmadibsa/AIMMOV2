"""
Conseiller IA NidBuyer — génération de fiches de décision d'achat.
Moteur : Google Gemini 1.5 Flash.

Principe anti-hallucination (approche RAG hybride) :
    Les données chiffrées (écart %, prix/m², médiane DVF, DPE) sont calculées
    EN AMONT par nos algorithmes from scratch (analysis/scoring.py).
    Gemini reçoit ces chiffres validés et est explicitement contraint
    à ne citer que les données fournies — jamais des inventions.

Variable d'environnement : GEMINI_API_KEY (ou GOOGLE_API_KEY en fallback).
"""

import logging
import os
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

MODEL      = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
MAX_TOKENS = 520   # ~3 sections Markdown courtes

# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Tu es NidBuyer, expert immobilier spécialisé sur Toulon et le Var.
Tu es direct, analytique et pragmatique. Ton rôle est d'aider des acheteurs \
à prendre une décision rapide et éclairée.

RÈGLES ABSOLUES :
1. Tu ne cites QUE les chiffres fournis dans le message utilisateur \
(prix, surface, écart marché, médiane, DPE). Tu n'inventes aucune donnée de marché.
2. Si une information clé manque (DPE inconnu, charges non renseignées…), \
tu le signales sans substituer une valeur fictive.
3. Tu rédiges en français, de façon concise et professionnelle.
4. Ta réponse est TOUJOURS structurée en exactement 3 sections Markdown :

### 1. Opportunité
### 2. Risques
### 3. Conseil de négociation

Pas d'introduction. Pas de conclusion. Directement les 3 sections.\
"""


# ── Construction du prompt utilisateur ───────────────────────────────────────

def _fmt_bool(val, label_vrai: str, label_faux: str = "Non") -> str:
    """Convertit un booléen/int ChromaDB en texte lisible."""
    return label_vrai if val else label_faux


def _build_user_prompt(bien: dict, mediane_m2: float | None, persona: dict) -> str:
    """
    Injecte les données calculées (from scratch) et les caractéristiques
    qualitatives (DPE, extérieurs, état) dans le prompt utilisateur.
    """
    # ── Données brutes ────────────────────────────────────────────────────────
    titre       = bien.get("titre")    or "Bien sans titre"
    quartier    = bien.get("quartier") or "Toulon"
    surface     = bien.get("surface")
    prix        = bien.get("prix")
    nb_pieces   = bien.get("nb_pieces")
    description = bien.get("document") or bien.get("description") or ""

    # ── Caractéristiques qualitatives (nouvelles colonnes Supabase) ───────────
    dpe      = bien.get("dpe")  or "Non renseigné"
    ges      = bien.get("ges")  or "Non renseigné"
    terrasse = _fmt_bool(bien.get("terrasse"), "Oui")
    balcon   = _fmt_bool(bien.get("balcon"),   "Oui")
    parking  = _fmt_bool(bien.get("parking"),  "Oui")
    travaux  = _fmt_bool(bien.get("travaux"),  "Signalés", "Non signalés")
    neuf     = _fmt_bool(bien.get("neuf"),     "Neuf", "Ancien")

    # ── Résultats mathématiques (from scratch — analysis/scoring.py) ──────────
    prix_m2   = bien.get("prix_m2")
    ecart_pct = bien.get("ecart_pct")
    label     = bien.get("label")  or "N/A"
    score     = bien.get("score")

    # ── Persona ───────────────────────────────────────────────────────────────
    persona_label = persona.get("label",      "Non précisé")
    profil_key    = persona.get("profil",     "")
    budget_max    = persona.get("budget_max")

    def _fp(v) -> str:
        return f"{int(v):,} €".replace(",", " ") if v else "N/A"

    def _fpct(v) -> str:
        return f"{v:+.1f} %" if v is not None else "N/A"

    def _fm2(v) -> str:
        return f"{int(v):,} €/m²".replace(",", " ") if v else "N/A"

    return f"""\
## Bien à analyser
- Titre    : {titre}
- Quartier : {quartier}
- Surface  : {surface} m²  |  {nb_pieces} pièces  |  {neuf}
- Prix     : {_fp(prix)}
- Description (extrait) : {str(description)[:500]}

## Caractéristiques techniques
- DPE : {dpe}  |  GES : {ges}
- Terrasse : {terrasse}  |  Balcon : {balcon}  |  Parking : {parking}
- Travaux  : {travaux}

## Validation mathématique (algorithmes NidBuyer — données DVF Supabase)
- Prix au m²            : {_fm2(prix_m2)}
- Médiane marché local  : {_fm2(mediane_m2)}
- Écart au marché       : {_fpct(ecart_pct)}  →  {label}
- Score opportunité     : {score}/100

## Profil acheteur ciblé
- Profil  : {persona_label}  ({profil_key})
- Budget  : {_fp(budget_max)}

Génère la fiche de décision (### 1. Opportunité / ### 2. Risques \
/ ### 3. Conseil de négociation).
Cite les chiffres et caractéristiques fournis ci-dessus. \
2-3 phrases par section, pas davantage.\
"""


# ── Fonction publique ─────────────────────────────────────────────────────────

def generer_conseil_achat(
    bien: dict,
    mediane_m2: float | None,
    persona: dict,
) -> str | None:
    """
    Génère une fiche de décision d'achat via Gemini 1.5 Flash.

    Args:
        bien      : dict fusionné — métadonnées ChromaDB + résultats scoring.
                    Champs exploités : prix, surface, quartier, dpe, terrasse,
                    balcon, parking, travaux, neuf, ecart_pct, score, document.
        mediane_m2: médiane €/m² du segment calculée from scratch.
        persona   : entrée du dict PERSONAS (label, profil, budget_max…).

    Returns:
        Texte Markdown de la fiche (str), ou None si l'appel échoue.
        Un retour None ne fait JAMAIS crasher la route appelante.
    """
    # Supporter GEMINI_API_KEY et GOOGLE_API_KEY (déjà dans le .env)
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error(
            "Ni GEMINI_API_KEY ni GOOGLE_API_KEY trouvé dans .env — "
            "conseil IA désactivé."
        )
        return None

    user_prompt = _build_user_prompt(bien, mediane_m2, persona)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(max_output_tokens=MAX_TOKENS),
        )
        response = model.generate_content(user_prompt)
        return response.text

    except Exception as e:
        # On attrape toutes les exceptions Gemini (google.api_core.exceptions.*)
        # pour ne jamais faire crasher la route appelante.
        err_type = type(e).__name__
        if "PermissionDenied" in err_type or "Unauthenticated" in err_type:
            logger.error("Clé API Gemini invalide : %s", e)
        elif "ResourceExhausted" in err_type:
            logger.warning("Quota Gemini atteint — fiche IA non générée.")
        elif "DeadlineExceeded" in err_type or "Timeout" in err_type:
            logger.warning("Timeout Gemini — fiche IA non générée.")
        else:
            logger.error("Erreur Gemini (%s) : %s", err_type, e)

    return None
