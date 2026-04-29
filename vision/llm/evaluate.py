"""
Module vision LLM — analyse de photos immobilières via Gemini Vision.

Entrée publique unique : analyser_photos(photos, ...) qui accepte indifféremment
des URLs http(s) ou des chemins locaux et retourne un dict structuré contenant à
la fois :
  - les champs typés du contrat de test (etat_general, travaux_detectes,
    estimation_travaux, luminosite, score_presentation)
  - les champs riches pour l'UI (etat_label, justification_etat, points_forts,
    points_vigilance, fourchette_travaux_eur)

build_markdown(parsed) reconstruit la fiche markdown affichable.
"""

import json
import logging
import os
import re as _re
from pathlib import Path

import google.generativeai as genai
import requests

logger = logging.getLogger(__name__)


def _ensure_genai_configured() -> None:
    """
    Configure le SDK Gemini avec la clé API au moment de l'appel (lazy).
    Permet d'utiliser ce module sans dépendre du backend (tests, scripts CLI),
    et sans imposer un ordre import-then-load_dotenv.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY (ou GOOGLE_API_KEY) absent — "
            "vérifiez votre fichier .env."
        )
    genai.configure(api_key=api_key)

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_MODEL = os.environ.get("GEMINI_VISION_MODEL", "gemma-4-26b-a4b-it")
MAX_IMAGES_HARD_LIMIT = 6   # plafond absolu (coût / latence Gemini)

# Vocabulaires contrôlés (alignés sur tests/test_vision.py)
ETATS_VALIDES        = ("excellent", "bon", "correct", "a_renover")
ESTIMATIONS_VALIDES  = ("0-5k", "5-20k", "20-50k", ">50k")
TRAVAUX_VOCAB        = (
    "peinture", "cuisine", "salle_de_bain", "sols", "fenetres",
    "toiture", "electricite", "plomberie", "isolation", "chauffage",
)

# ── Prompt système ────────────────────────────────────────────────────────────

VISION_PROMPT = (
    "Tu es un expert en évaluation immobilière. Analyse les photos d'un bien et "
    "renvoie EXCLUSIVEMENT un objet JSON valide. AUCUN texte hors du JSON. "
    "AUCUN préambule, AUCune réflexion, AUCune description photo par photo, "
    "AUCune note d'auto-correction.\n\n"
    "Toutes les valeurs textuelles libres doivent être EN FRANÇAIS, factuelles, "
    "courtes et basées uniquement sur ce qui est visible.\n\n"
    "Schéma JSON OBLIGATOIRE (respecte exactement les clés, types et énumérations) :\n"
    "{\n"
    '  "etat_general": "<excellent | bon | correct | a_renover>",\n'
    '  "etat_label": "<Neuf | Bon état | Bon état / À rafraîchir | À rafraîchir | '
    'À rénover | Lourde rénovation>",\n'
    '  "justification_etat": "<1 à 2 phrases factuelles>",\n'
    '  "points_forts": ["point 1", "point 2", "point 3"],          // 3 à 5 items\n'
    '  "points_vigilance": ["défaut/travaux 1", "défaut/travaux 2"], // 2 à 5 items\n'
    '  "travaux_detectes": ["peinture", "cuisine", "salle_de_bain"], // vocabulaire '
    "contrôlé : peinture, cuisine, salle_de_bain, sols, fenetres, toiture, "
    "electricite, plomberie, isolation, chauffage\n"
    '  "estimation_travaux": "<0-5k | 5-20k | 20-50k | >50k>",\n'
    '  "fourchette_travaux_eur": "<min> - <max> € — brève justification (ex: '
    "'5 000 - 9 000 € — rafraîchissement cuisine + salle de bain')\",\n"
    '  "luminosite": <entier de 1 à 5>,\n'
    '  "score_presentation": <entier de 1 à 10>\n'
    "}\n\n"
    "Règles de cohérence :\n"
    "- 'etat_general' doit correspondre à 'etat_label' (ex: Neuf/Bon état → 'excellent' "
    "ou 'bon' ; À rafraîchir → 'correct' ; À rénover/Lourde rénovation → 'a_renover').\n"
    "- 'estimation_travaux' doit être cohérent avec la fourchette en euros.\n"
    "- 'travaux_detectes' ne contient QUE les valeurs autorisées du vocabulaire.\n\n"
    "Si les photos sont insuffisantes pour un point, écris-le dans la valeur "
    "concernée (ex: 'Photos insuffisantes pour estimer.'). Réponds par le JSON "
    "et rien d'autre."
)

# ── Fallback en cas d'échec de parsing JSON ───────────────────────────────────

_FALLBACK_RESULT = {
    "etat_general":           "correct",
    "etat_label":             "Analyse non disponible",
    "justification_etat":     "Réponse modèle invalide.",
    "points_forts":           [],
    "points_vigilance":       [],
    "travaux_detectes":       [],
    "estimation_travaux":     "5-20k",
    "fourchette_travaux_eur": "Non estimable",
    "luminosite":             3,
    "score_presentation":     5,
}


# ── Helpers privés : parsing JSON robuste ────────────────────────────────────

def _parse_json_response(text: str) -> dict:
    """Extrait le 1er objet JSON valide non-vide de la réponse du modèle."""
    if not text:
        return dict(_FALLBACK_RESULT)

    # Suppression des fences ```json … ``` et des balises de raisonnement
    cleaned = _re.sub(r"```(?:json)?\s*", "", text, flags=_re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    cleaned = _re.sub(
        r"<(reflexion|think|thinking|raisonnement|answer)>.*?</(reflexion|think|thinking|raisonnement|answer)>",
        "", cleaned, flags=_re.DOTALL | _re.IGNORECASE,
    )

    # 1. tout le texte est-il un JSON ?
    candidates: list[str] = []
    stripped = cleaned.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)

    # 2. extraction de toutes les sous-chaînes { ... } équilibrées
    depth = 0
    start = -1
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(cleaned[start : i + 1])
                start = -1

    expected_keys = {"etat_general", "estimation_travaux", "luminosite", "score_presentation"}
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and expected_keys & obj.keys():
            return _normalize_vision_dict(obj)

    return dict(_FALLBACK_RESULT)


def _coerce_int(v, lo: int, hi: int, default: int) -> int:
    """Convertit en int et clamp dans [lo, hi]. default si invalide."""
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _coerce_enum(v, valid: tuple, default: str) -> str:
    """Force la valeur dans l'enum (case-insensitive, accepte des variantes proches)."""
    if not isinstance(v, str):
        return default
    s = v.strip().lower().replace(" ", "_").replace("-", "_")
    for opt in valid:
        if opt.lower().replace("-", "_") == s:
            return opt
    # Variantes courantes
    aliases = {
        "à_rénover": "a_renover", "a_rénover": "a_renover",
        "à_renover": "a_renover", "renover": "a_renover",
        "lourde_rénovation": "a_renover", "à_rafraîchir": "correct",
        "a_rafraichir": "correct", "rafraichir": "correct",
        "neuf": "excellent",
    }
    if s in aliases and aliases[s] in valid:
        return aliases[s]
    return default


def _coerce_list(v, vocab: tuple | None = None) -> list[str]:
    """Convertit en list[str], filtre par vocabulaire si fourni."""
    if isinstance(v, list):
        items = [str(x).strip() for x in v if str(x).strip()]
    elif isinstance(v, str) and v.strip():
        parts = _re.split(r"\n[-•*]\s*|\s*[•*]\s+|,\s*", v.strip())
        items = [p.strip("- ").strip() for p in parts if p.strip()]
    else:
        return []
    if vocab is not None:
        normalized = []
        vocab_lc = {x.lower() for x in vocab}
        for it in items:
            key = it.lower().replace(" ", "_").replace("-", "_")
            if key in vocab_lc:
                normalized.append(key)
        return normalized
    return items


def _normalize_vision_dict(obj: dict) -> dict:
    """Sanitize/typifie le JSON retourné par le modèle pour respecter les contrats."""
    return {
        "etat_general":           _coerce_enum(obj.get("etat_general"), ETATS_VALIDES, "correct"),
        "etat_label":             str(obj.get("etat_label") or "—").strip(),
        "justification_etat":     str(obj.get("justification_etat") or "").strip(),
        "points_forts":           _coerce_list(obj.get("points_forts")),
        "points_vigilance":       _coerce_list(obj.get("points_vigilance")),
        "travaux_detectes":       _coerce_list(obj.get("travaux_detectes"), TRAVAUX_VOCAB),
        "estimation_travaux":     _coerce_enum(obj.get("estimation_travaux"), ESTIMATIONS_VALIDES, "5-20k"),
        "fourchette_travaux_eur": str(obj.get("fourchette_travaux_eur") or "—").strip(),
        "luminosite":             _coerce_int(obj.get("luminosite"), 1, 5, 3),
        "score_presentation":     _coerce_int(obj.get("score_presentation"), 1, 10, 5),
    }


# ── Helpers privés : chargement images (URL ou disque) ───────────────────────

def _load_image_payload(source: str) -> dict | None:
    """Charge une image (URL http(s) ou chemin local) en {mime_type, data}."""
    try:
        if source.startswith(("http://", "https://")):
            r = requests.get(source, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            data = r.content
        else:
            p = Path(source)
            if not p.is_file():
                logger.warning("Image introuvable : %s", source)
                return None
            mime = _MIME_BY_EXT.get(p.suffix.lower(), "image/jpeg")
            data = p.read_bytes()
        if not mime.startswith("image/"):
            mime = "image/jpeg"
        return {"mime_type": mime, "data": data}
    except Exception as e:
        logger.warning("Chargement image échoué (%s) : %s", source, e)
        return None


_MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp",
    ".gif": "image/gif", ".bmp": "image/bmp",
}


def _build_user_prompt(titre: str | None, type_bien: str | None) -> str:
    contexte = []
    if titre:     contexte.append(f"Titre : {titre}")
    if type_bien: contexte.append(f"Type : {type_bien}")
    if contexte:
        return "Contexte du bien : " + " | ".join(contexte) + "\n\n" + VISION_PROMPT
    return VISION_PROMPT


# ── API publique ──────────────────────────────────────────────────────────────

def analyser_photos(
    photos: list[str],
    titre: str | None = None,
    type_bien: str | None = None,
    max_images: int = 4,
    model_name: str | None = None,
) -> dict:
    """
    Analyse vision unifiée — accepte URLs http(s) ou chemins locaux.

    Returns:
        Dict normalisé avec tous les champs (cf. _FALLBACK_RESULT).

    Raises:
        ValueError   : aucune photo exploitable / aucune n'a pu être chargée.
        RuntimeError : appel Gemini en échec.
    """
    if not photos:
        raise ValueError("Au moins une photo est requise.")

    sources = [s for s in photos if isinstance(s, str) and s.strip()]
    if not sources:
        raise ValueError("Aucune source de photo exploitable.")

    n = max(1, min(max_images, MAX_IMAGES_HARD_LIMIT))
    images_payload = [p for p in (_load_image_payload(s) for s in sources[:n]) if p]
    if not images_payload:
        raise ValueError("Impossible de charger les photos fournies (URL ou fichier).")

    _ensure_genai_configured()
    model_id = model_name or DEFAULT_MODEL

    def _call_model(force_json: bool):
        gen_cfg_kwargs = {"temperature": 0.1, "max_output_tokens": 1100}
        if force_json:
            gen_cfg_kwargs["response_mime_type"] = "application/json"
        m = genai.GenerativeModel(
            model_id,
            generation_config=genai.GenerationConfig(**gen_cfg_kwargs),
        )
        return m.generate_content([_build_user_prompt(titre, type_bien), *images_payload])

    try:
        try:
            response = _call_model(force_json=True)
        except Exception as e_json:
            logger.info("Mime JSON refusé (%s) — retry sans contrainte.", type(e_json).__name__)
            response = _call_model(force_json=False)
        raw = (response.text or "").strip()
    except Exception as e:
        logger.error("Erreur Gemini Vision : %s", e)
        raise RuntimeError(f"Erreur Gemini Vision : {e}") from e

    parsed = _parse_json_response(raw)
    parsed["_n_images"] = len(images_payload)
    parsed["_model"]    = model_id
    return parsed


def build_markdown(parsed: dict) -> str:
    """Reconstruit la fiche markdown affichable depuis un dict normalisé."""
    pf = parsed.get("points_forts") or []
    pv = parsed.get("points_vigilance") or []

    pf_md = "\n".join(f"- {p}" for p in pf) if pf else "- _Non renseigné_"
    pv_md = "\n".join(f"- {p}" for p in pv) if pv else "- _Non renseigné_"

    etat_titre = parsed.get("etat_label") or parsed.get("etat_general", "—")
    justif     = parsed.get("justification_etat", "")
    etat_block = f"**{etat_titre}**" + (f" — {justif}" if justif else "")

    budget = parsed.get("fourchette_travaux_eur") or parsed.get("estimation_travaux", "—")

    extras = []
    if "luminosite" in parsed:
        extras.append(f"💡 Luminosité : {parsed['luminosite']}/5")
    if "score_presentation" in parsed:
        extras.append(f"📸 Présentation : {parsed['score_presentation']}/10")
    extras_md = "  ·  ".join(extras)

    return (
        f"### 🏠 État général\n{etat_block}\n\n"
        f"### ✅ Points forts\n{pf_md}\n\n"
        f"### ⚠️ Points de vigilance / travaux à prévoir\n{pv_md}\n\n"
        f"### 💰 Estimation budget travaux\n{budget}"
        + (f"\n\n_{extras_md}_" if extras_md else "")
    )


# ── Compatibilité ascendante ─────────────────────────────────────────────────

def analyser_bien_par_urls(
    urls: list[str],
    titre: str | None = None,
    type_bien: str | None = None,
    max_images: int = 4,
    model_name: str | None = None,
) -> dict:
    """Wrapper conservé pour l'endpoint /api/analyse-images du backend."""
    parsed = analyser_photos(urls, titre, type_bien, max_images, model_name)
    return {
        "analyse":            build_markdown(parsed),
        "analyse_structuree": parsed,
        "n_images":           parsed.get("_n_images", 0),
        "model":              parsed.get("_model", DEFAULT_MODEL),
    }


def evaluer_photos_gemini(photos: list, model_name: str = DEFAULT_MODEL) -> str:
    """
    Version legacy (chemins locaux uniquement, retourne du texte libre).
    Conservée pour les scripts CLI / benchmarks. Utilise le SDK google.genai
    (lazy import pour ne pas casser le backend si ce package est absent).
    """
    from google import genai as _new_genai
    from PIL import Image

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("La variable d'environnement GEMINI_API_KEY n'est pas définie.")

    client = _new_genai.Client(api_key=api_key)
    prompt = (
        "Voici plusieurs photos d'un bien immobilier. Analyse son état général, "
        "identifie les points forts et les éventuels travaux ou défauts visibles. "
        "Synthétise ton analyse."
    )
    content = [prompt]
    for photo_path in photos[:4]:
        try:
            content.append(Image.open(photo_path))
        except Exception as e:
            logger.warning("Erreur lors du chargement de %s : %s", photo_path, e)

    try:
        response = client.models.generate_content(model=model_name, contents=content)
        return response.text
    except Exception as e:
        logger.error("Erreur API Gemini : %s", e)
        return ""


# ── CLI de test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    sample = Path(__file__).resolve().parents[2] / "tests" / "img" / "cuisine-rénover.webp"
    print(f"Analyse de : {sample}")
    print(json.dumps(analyser_photos([str(sample)]), indent=2, ensure_ascii=False))
