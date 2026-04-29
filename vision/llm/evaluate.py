"""
Module vision LLM — analyse de photos immobilières via Gemini Vision.

Deux entrées publiques :
  - analyser_bien_par_urls(...) : utilisé par le backend FastAPI (/api/analyse-images).
    Télécharge les photos depuis leurs URLs, appelle Gemini Vision, nettoie la sortie.
  - evaluer_photos_gemini(...)  : version locale (chemins de fichiers) — utilisée pour
    les tests / scripts CLI. Conservée pour compatibilité avec les notebooks/benchmarks.
"""

import json
import logging
import os
import re as _re
from pathlib import Path

import google.generativeai as genai
import requests

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_MODEL = os.environ.get("GEMINI_VISION_MODEL", "gemma-4-26b-a4b-it")
MAX_IMAGES_HARD_LIMIT = 6   # plafond absolu (coût / latence Gemini)

# ── Prompt système ────────────────────────────────────────────────────────────

VISION_PROMPT = (
    "Tu es un expert en évaluation immobilière. Analyse les photos d'un bien et "
    "renvoie EXCLUSIVEMENT un objet JSON valide. AUCUN texte hors du JSON. "
    "AUCUN préambule, AUCune réflexion, AUCune description photo par photo, "
    "AUCune note d'auto-correction.\n\n"
    "Toutes les valeurs textuelles doivent être EN FRANÇAIS, factuelles, "
    "courtes et basées uniquement sur ce qui est visible.\n\n"
    "Schéma JSON OBLIGATOIRE (respecte exactement les clés et les types) :\n"
    "{\n"
    '  "etat_general": "<Neuf | Bon état | Bon état / À rafraîchir | À rafraîchir | '
    'À rénover | Lourde rénovation> — 1 à 2 phrases de justification.",\n'
    '  "points_forts": ["point 1", "point 2", "point 3"],          // 3 à 5 items\n'
    '  "points_vigilance": ["défaut/travaux 1", "défaut/travaux 2"], // 2 à 5 items\n'
    '  "budget_travaux": "<min> - <max> € — brève justification (ex: \'5 000 - 9 000 € — '
    "rafraîchissement cuisine + salle de bain\\').\"\n"
    "}\n\n"
    "Si les photos sont insuffisantes pour estimer un point, écris-le explicitement "
    "dans la valeur concernée (ex: \"Photos insuffisantes pour estimer.\"). "
    "Réponds par le JSON et rien d'autre."
)


# Schéma de fallback si le LLM ne respecte pas le JSON
_FALLBACK_RESULT = {
    "etat_general":     "Analyse non disponible.",
    "points_forts":     [],
    "points_vigilance": [],
    "budget_travaux":   "Non estimable (réponse modèle invalide).",
}


# ── Helpers privés ────────────────────────────────────────────────────────────

_THINKING_PREFIXES = (
    "input:", "goal:", "plan:", "step ", "note:", "observation:",
    "thought:", "reasoning:", "analysis:", "context:", "output:",
    "réflexion:", "raisonnement:", "étape ", "objectif:", "analyse:",
    "self-correction:", "draft:", "photo 1", "photo 2", "photo 3",
)


def _parse_json_response(text: str) -> dict:
    """
    Extrait un objet JSON valide depuis la réponse brute du modèle, même si :
      - le LLM enveloppe le JSON dans ```json ... ```
      - le LLM ajoute du préambule/raisonnement avant ou après
      - le LLM produit plusieurs blocs JSON (on prend le 1er valide non-vide)

    Retourne un dict respectant le schéma {etat_general, points_forts,
    points_vigilance, budget_travaux} — complète avec _FALLBACK_RESULT si
    parsing impossible.
    """
    if not text:
        return dict(_FALLBACK_RESULT)

    # 1. Suppression des fences ```json … ```
    cleaned = _re.sub(r"```(?:json)?\s*", "", text, flags=_re.IGNORECASE)
    cleaned = cleaned.replace("```", "")

    # 2. Suppression des blocs de réflexion <think>...</think> éventuels
    cleaned = _re.sub(
        r"<(reflexion|think|thinking|raisonnement|answer)>.*?</(reflexion|think|thinking|raisonnement|answer)>",
        "", cleaned, flags=_re.DOTALL | _re.IGNORECASE,
    )

    # 3. Tentative directe : tout le texte est-il un JSON ?
    candidates: list[str] = []
    stripped = cleaned.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)

    # 4. Sinon, on extrait toutes les sous-chaînes { ... } équilibrées
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

    # 5. Première candidate qui parse en dict avec au moins une clé attendue
    expected_keys = {"etat_general", "points_forts", "points_vigilance", "budget_travaux"}
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and expected_keys & obj.keys():
            return _normalize_vision_dict(obj)

    return dict(_FALLBACK_RESULT)


def _normalize_vision_dict(obj: dict) -> dict:
    """Sanitize/typifie le JSON retourné par le modèle."""
    def _as_list(v) -> list[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            # Le modèle peut renvoyer une string avec puces — on splitte.
            parts = _re.split(r"\n[-•*]\s*|\s*[•*]\s+", v.strip())
            return [p.strip("- ").strip() for p in parts if p.strip()]
        return []

    return {
        "etat_general":     str(obj.get("etat_general") or _FALLBACK_RESULT["etat_general"]).strip(),
        "points_forts":     _as_list(obj.get("points_forts")),
        "points_vigilance": _as_list(obj.get("points_vigilance")),
        "budget_travaux":   str(obj.get("budget_travaux") or _FALLBACK_RESULT["budget_travaux"]).strip(),
    }


def _build_markdown(parsed: dict) -> str:
    """Reconstruit la fiche markdown affichable depuis le JSON normalisé."""
    pf = parsed.get("points_forts") or []
    pv = parsed.get("points_vigilance") or []

    pf_md = "\n".join(f"- {p}" for p in pf) if pf else "- _Non renseigné_"
    pv_md = "\n".join(f"- {p}" for p in pv) if pv else "- _Non renseigné_"

    return (
        f"### 🏠 État général\n{parsed.get('etat_general', '—')}\n\n"
        f"### ✅ Points forts\n{pf_md}\n\n"
        f"### ⚠️ Points de vigilance / travaux à prévoir\n{pv_md}\n\n"
        f"### 💰 Estimation budget travaux\n{parsed.get('budget_travaux', '—')}"
    )


def _download_images_from_urls(urls: list[str], max_n: int) -> list[dict]:
    """Télécharge les images et retourne une liste de payloads {mime_type, data}."""
    payloads: list[dict] = []
    n = max(1, min(max_n, MAX_IMAGES_HARD_LIMIT))
    for url in urls[:n]:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            if not mime.startswith("image/"):
                mime = "image/jpeg"
            payloads.append({"mime_type": mime, "data": r.content})
        except Exception as e:
            logger.warning("Téléchargement image échoué (%s) : %s", url, e)
    return payloads


def _build_user_prompt(titre: str | None, type_bien: str | None) -> str:
    contexte = []
    if titre:     contexte.append(f"Titre : {titre}")
    if type_bien: contexte.append(f"Type : {type_bien}")
    if contexte:
        return "Contexte du bien : " + " | ".join(contexte) + "\n\n" + VISION_PROMPT
    return VISION_PROMPT


# ── API publique ──────────────────────────────────────────────────────────────

def analyser_bien_par_urls(
    urls: list[str],
    titre: str | None = None,
    type_bien: str | None = None,
    max_images: int = 4,
    model_name: str | None = None,
) -> dict:
    """
    Analyse vision d'un bien à partir des URLs de ses photos.

    Args:
        urls       : liste d'URLs http(s) des photos.
        titre      : titre de l'annonce (contexte).
        type_bien  : Appartement / Maison / etc. (contexte).
        max_images : plafonné à MAX_IMAGES_HARD_LIMIT (6).
        model_name : surcharge optionnelle du modèle Gemini.

    Returns:
        {"analyse": str, "n_images": int, "model": str}

    Raises:
        ValueError : aucune photo exploitable / impossible de télécharger.
        RuntimeError : appel Gemini en échec.
    """
    photos = [u for u in (urls or []) if isinstance(u, str) and u.startswith("http")]
    if not photos:
        raise ValueError("Aucune URL de photo exploitable.")

    images_payload = _download_images_from_urls(photos, max_images)
    if not images_payload:
        raise ValueError("Impossible de télécharger les photos fournies.")

    model_id = model_name or DEFAULT_MODEL

    # On essaie d'abord avec response_mime_type="application/json" (Gemini standard).
    # Si Gemma refuse cette option, on retombe sur un appel sans contrainte mime
    # (le prompt demande déjà du JSON et _parse_json_response est robuste).
    def _call_model(force_json: bool):
        gen_cfg_kwargs = {"temperature": 0.1, "max_output_tokens": 900}
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

    parsed   = _parse_json_response(raw)
    markdown = _build_markdown(parsed)

    return {
        "analyse":            markdown,    # markdown reconstruit (affiché par le frontend)
        "analyse_structuree": parsed,      # JSON brut (utilisable par d'autres clients)
        "n_images":           len(images_payload),
        "model":              model_id,
    }


def evaluer_photos_gemini(photos: list, model_name: str = DEFAULT_MODEL) -> str:
    """
    Version locale (chemins de fichiers) — conservée pour compatibilité avec les
    scripts CLI / benchmarks. Utilise le nouveau SDK google.genai (lazy import).
    Limite à 4 photos.
    """
    from google import genai as _new_genai     # lazy import pour ne pas casser le backend
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

    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)

    chemin_image = Path(__file__).resolve().parents[1] / "img" / "cuisine-rénover.webp"
    print(f"Lancement de l'analyse avec l'image : {chemin_image}")
    print("\n--- Résultat de l'analyse ---")
    print(evaluer_photos_gemini([str(chemin_image)]))
