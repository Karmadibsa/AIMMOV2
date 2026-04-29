"""
NidBuyer V2 — Backend FastAPI
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import re as _re
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from queue import Queue

from dotenv import load_dotenv
import google.generativeai as genai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Chargement du .env avant tout accès à os.environ
load_dotenv(Path(__file__).parent.parent / ".env")

from .ingestion import sync

logger = logging.getLogger(__name__)

# Modèle chat configurable via GEMMA_MODEL dans .env
_CHAT_MODEL    = os.environ.get("GEMMA_MODEL",          "gemma-4-27b-it")
# Modèle léger pour l'extraction JSON (rapide, moins coûteux)
_EXTRACT_MODEL = os.environ.get("GEMINI_EXTRACT_MODEL", "gemini-1.5-flash")

# ── Configuration Globale Gemini ──────────────────────────────────────────────
_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if _api_key:
    genai.configure(api_key=_api_key)
else:
    logger.warning("⚠️ Clé GEMINI_API_KEY introuvable dans l'environnement au démarrage.")

scheduler = AsyncIOScheduler()


# ── Utilitaire nettoyage sorties LLM ──────────────────────────────────────────────

_THINKING_PREFIXES = (
    "input:", "goal:", "plan:", "step ", "note:", "observation:",
    "thought:", "reasoning:", "analysis:", "context:", "output:",
    "réflexion:", "raisonnement:", "étape ", "objectif:", "analyse:",
    "greeting:", "language:",
)

def _clean_llm_output(text: str) -> str:
    """Extrait <ANSWER>…</ANSWER> ou supprime les artefacts de raisonnement Gemma.

    Priorité absolue : si <ANSWER> est présent, TOUT ce qui est en dehors est supprimé
    (y compris <reflexion>, <think>, et tout préambule).
    """
    if not text:
        return text

    # Passage 1 : suppression de tous les blocs de raisonnement AVANT extraction
    cleaned = _re.sub(
        r"<(reflexion|think|thinking|raisonnement)>.*?</(reflexion|think|thinking|raisonnement)>",
        "", text, flags=_re.DOTALL | _re.IGNORECASE
    )

    # Passage 2 : extraction stricte entre <ANSWER>…</ANSWER>
    match = _re.search(r"<ANSWER>(.*?)</ANSWER>", cleaned, _re.DOTALL | _re.IGNORECASE)
    if match:
        return _re.sub(r"\n{3,}", "\n\n", match.group(1).strip())

    # Fallback : si pas de balise ANSWER, nettoyage heuristique
    lines = [l for l in cleaned.splitlines()
             if not any(l.strip().lower().startswith(p) for p in _THINKING_PREFIXES)]
    text = "\n".join(lines)
    lower = text.lower()
    for marker in ("## ", "**", "bonjour", "je ", "voici", "bien sûr",
                   "pour votre", "j'ai trouvé", "parmi les"):
        idx = lower.find(marker)
        if 0 < idx < 400:
            text = text[idx:]
            break
    return _re.sub(r"\n{3,}", "\n\n", text).strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(sync, "cron", hour=11, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="NidBuyer API", version="0.2.0", lifespan=lifespan)

# ── CORS ─────────────────────────────────────────────────────────────────────
# allow_origins=["*"] couvre Streamlit Cloud + tout frontend pendant la phase de lancement.
# Restreindre à l'URL Streamlit exacte une fois le domaine stable.
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modèles ───────────────────────────────────────────────────────────────────

class ProfilAcheteur(BaseModel):
    intention: str = "rp"       # "rp" | "rs" | "investissement" | "mixte"
    budget_max: float | None = None
    surface_min: float | None = None
    quartiers: list[str] = []
    nb_pieces_min: int | None = None
    description_libre: str = ""


class AlerteProfil(BaseModel):
    email: str
    nom_alerte: str = "Mes critères"
    profil: ProfilAcheteur


class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []
    n_context: int = 5


class AnalyseImagesRequest(BaseModel):
    photos: list[str]                # URLs des photos du bien
    titre: str | None = None
    type_bien: str | None = None
    max_images: int = 4              # plafond pour limiter le coût/latence


# ── Nettoyage sortie LLM ─────────────────────────────────────────────────────

_THINKING_PREFIXES = (
    "input:", "goal:", "plan:", "step ", "note:", "observation:",
    "thought:", "reasoning:", "analysis:", "context:", "output:",
    "réflexion:", "raisonnement:", "étape ", "objectif:", "analyse:",
)

def _clean_llm_output(text: str) -> str:
    """Extrait <ANSWER>…</ANSWER> ou supprime les artefacts de raisonnement Gemma."""
    if not text:
        return text
    # 1. Balise <ANSWER> (méthode primaire)
    match = _re.search(r"<ANSWER>(.*?)</ANSWER>", text, _re.DOTALL)
    if match:
        return match.group(1).strip()
    # 2. Blocs <think>
    text = _re.sub(r"<think>.*?</think>", "", text, flags=_re.DOTALL | _re.IGNORECASE)
    # 3. Lignes de raisonnement préfixées
    lines = [l for l in text.splitlines()
             if not any(l.strip().lower().startswith(p) for p in _THINKING_PREFIXES)]
    text = "\n".join(lines)
    # 4. Tronquer avant le premier marqueur conversationnel
    lower = text.lower()
    for marker in ("bonjour", "je ", "voici", "bien sûr", "d'accord",
                   "pour votre", "j'ai trouvé", "parmi les"):
        idx = lower.find(marker)
        if 0 < idx < 300:
            text = text[idx:]
            break
    return _re.sub(r"\n{3,}", "\n\n", text).strip()


# ── Helpers partagés ──────────────────────────────────────────────────────────

def _build_chroma_filters(
    budget_max: float | None,
    surface_min: float | None,
    nb_pieces_min: int | None,
    type_bien: str | None = None,
) -> dict:
    """Construit un filtre ChromaDB $and depuis les contraintes du profil."""
    conditions: list[dict] = [{"prix": {"$gt": 0.0}}]
    if budget_max:
        conditions.append({"prix": {"$lte": float(budget_max)}})
    if surface_min:
        conditions.append({"surface": {"$gte": float(surface_min)}})
    if nb_pieces_min:
        conditions.append({"nb_pieces": {"$gte": float(nb_pieces_min)}})
    if type_bien in ("Appartement", "Maison"):
        conditions.append({"type_bien": {"$eq": type_bien}})
    return {"$and": conditions} if len(conditions) > 1 else conditions[0]


def _score_candidats(candidats: list[dict], profil_str: str, n: int) -> tuple[list[dict], float | None]:
    """
    Calcule la médiane €/m² et score chaque candidat.
    Retourne (liste_scorée_triée[:n], mediane_m2).
    """
    from .analysis.stats import median
    from .analysis.scoring import score_opportunite

    prix_m2_list = [
        r["prix"] / r["surface"]
        for r in candidats
        if r.get("prix", 0) > 0 and r.get("surface", 0) > 0
    ]
    mediane_m2: float | None = median(prix_m2_list) if len(prix_m2_list) >= 2 else None

    scored: list[dict] = []
    for r in candidats:
        sc = (
            score_opportunite(r, mediane_m2, profil_str)
            if mediane_m2 else
            {"prix_m2": None, "ecart_pct": None, "label": "N/A", "score": None, "opportunite": False}
        )
        scored.append({
            "id":        r["id"],
            "lien":      r.get("lien"),
            "titre":     r.get("titre"),
            "quartier":  r.get("quartier"),
            "surface":   r.get("surface"),
            "prix":      r.get("prix"),
            "nb_pieces": r.get("nb_pieces"),
            "dpe":       r.get("dpe"),
            "terrasse":  r.get("terrasse", 0),
            "balcon":    r.get("balcon", 0),
            "parking":   r.get("parking", 0),
            "travaux":   r.get("travaux", 0),
            "latitude":  r.get("latitude", 0.0),
            "longitude": r.get("longitude", 0.0),
            "distance":  r["distance"],
            "document":  r.get("document", ""),
            **sc,
        })

    avec_score = [s for s in scored if s["score"] is not None]
    avec_score.sort(key=lambda x: x["score"], reverse=True)
    return avec_score[:n], mediane_m2


# ── POST /rechercher ──────────────────────────────────────────────────────────

@app.post("/rechercher")
def rechercher(profil: ProfilAcheteur, n: int = 5):
    """
    Profil acheteur → top N biens avec scores et fiche IA pour le #1.

    Pipeline :
      1. Construit les filtres ChromaDB depuis les champs du profil.
      2. Recherche sémantique dans ChromaDB (oversample ×3).
      3. Calcule la médiane €/m² from scratch.
      4. Score chaque candidat via score_opportunite().
      5. Génère un avis IA Gemini pour le bien classé #1.
    """
    from .rag import search_similar
    from .llm_advisor import generer_conseil_achat

    # Requête sémantique construite depuis le profil
    query_parts: list[str] = []
    if profil.intention == "rp":
        query_parts.append("appartement familial calme proche écoles transports en commun")
    elif profil.intention == "investissement":
        query_parts.append("studio T2 rendement locatif centre-ville proche gare")
    elif profil.intention == "rs":
        query_parts.append("vue mer résidence secondaire calme plage Toulon")
    else:
        query_parts.append("immeuble de rapport logements investissement mixte")

    if profil.quartiers:
        query_parts.append(", ".join(profil.quartiers))
    if profil.description_libre:
        query_parts.append(profil.description_libre)

    query = " — ".join(query_parts)

    filtre = _build_chroma_filters(profil.budget_max, profil.surface_min, profil.nb_pieces_min)
    candidats = search_similar(query=query, n_results=max(n * 3, 15), filtre_meta=filtre)

    if not candidats:
        return {"recommandations": [], "mediane_m2": None, "n_candidats": 0}

    top_n, mediane_m2 = _score_candidats(candidats, profil.intention, n)

    if top_n:
        persona_virtuel = {
            "label":      profil.intention.upper(),
            "profil":     profil.intention,
            "budget_max": profil.budget_max,
        }
        top_n[0]["avis_ia"] = generer_conseil_achat(top_n[0], mediane_m2, persona_virtuel)

    for item in top_n:
        item.pop("document", None)

    return {
        "recommandations": top_n,
        "mediane_m2":      round(mediane_m2, 2) if mediane_m2 else None,
        "n_candidats":     len(candidats),
    }


# ── GET /api/recommendations/{persona_id} ─────────────────────────────────────

@app.get("/api/recommendations/{persona_id}")
def recommendations(persona_id: str, n: int = 5):
    """
    Top N opportunités pour un persona prédéfini (RP / INV / RS / MIX).

    Pipeline :
      1. Charge les filtres et la requête du persona.
      2. Recherche sémantique ChromaDB (oversample ×3).
      3. Médiane €/m² from scratch → score chaque candidat.
      4. Avis IA Gemini pour le #1.
    """
    from .personas import PERSONAS, PERSONA_IDS
    from .rag import search_similar
    from .llm_advisor import generer_conseil_achat

    pid = persona_id.upper()
    if pid not in PERSONAS:
        raise HTTPException(
            status_code=404,
            detail=f"Persona '{persona_id}' inconnu. Valeurs acceptées : {PERSONA_IDS}",
        )

    persona = PERSONAS[pid]

    candidats = search_similar(
        query=persona["query"],
        n_results=max(n * 3, 15),
        filtre_meta=persona["filters"],
    )

    if not candidats:
        return {
            "persona":         pid,
            "label":           persona["label"],
            "supabase_count":  0,
            "mediane_m2":      None,
            "recommandations": [],
            "message":         "Aucun bien trouvé pour ce profil dans ChromaDB.",
        }

    top_n, mediane_m2 = _score_candidats(candidats, persona["profil"], n)

    if top_n:
        top_n[0]["avis_ia"] = generer_conseil_achat(top_n[0], mediane_m2, persona)

    for item in top_n:
        item.pop("document", None)

    return {
        "persona":         pid,
        "label":           persona["label"],
        "budget_max":      persona.get("budget_max"),
        "n_candidats":     len(candidats),
        "mediane_m2":      round(mediane_m2, 2) if mediane_m2 else None,
        "recommandations": top_n,
    }


# ── POST /api/chat ────────────────────────────────────────────────────────────

@app.post("/api/chat")
def chat_ia(req: ChatRequest):
    """
    Conversation libre → réponse Gemini + profil extrait + biens correspondants.

    Pipeline :
      1. Gemini extrait le profil acheteur depuis la conversation (JSON).
      2. Construit les filtres ChromaDB depuis le profil extrait.
      3. Recherche sémantique ChromaDB (n_context biens).
      4. Gemini répond en langage naturel en se basant sur les biens trouvés.

    Returns:
        reponse          : str — réponse conversationnelle Gemini.
        profil_detecte   : dict — profil extrait de la conversation.
        biens_trouves    : list — biens ChromaDB correspondants (sans document interne).
        n_biens_contexte : int
    """
    from .rag import search_similar
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("🚨 ÉCHEC API CHAT: GEMINI_API_KEY manquant. Vérifiez votre fichier .env.")
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY manquant dans .env. Impossible d'appeler le LLM.")

    profil_detecte: dict = {
        "intention": None, "type_bien": None, "budget_max": None,
        "surface_min": None, "nb_pieces_min": None,
        "quartiers": [], "description_libre": "",
    }

    # ── Détection analyse directe de fiche (bypass extraction + ChromaDB) ─────
    # La question envoyée par le bouton "Analyser" commence toujours par ce texte
    # (début du template fiche_decision_v3.txt formaté).
    _is_fiche = req.question.lstrip().startswith("Voici les informations sur le bien")

    biens: list[dict] = []

    if not _is_fiche:
        # ── 1. Extraction du profil acheteur (modèle flash = rapide) ─────────
        history_text = "\n".join(
            f"{m.role.upper()}: {m.content}"
            for m in req.history[-8:]
        )
        extraction_prompt = (
            "Analyse cette conversation d'un acheteur immobilier à Toulon "
            "et extrais son profil. Retourne UNIQUEMENT un JSON valide.\n\n"
            f"HISTORIQUE :\n{history_text}\n"
            f"NOUVEAU MESSAGE : {req.question}\n\n"
            'JSON attendu (utilise null si inconnu) :\n'
            '{\n'
            '  "intention": "rp" | "rs" | "investissement" | "mixte" | null,\n'
            '  "type_bien": "Appartement" | "Maison" | null,\n'
            '  "budget_max": <float en euros ou null>,\n'
            '  "surface_min": <float en m² ou null>,\n'
            '  "nb_pieces_min": <int ou null>,\n'
            '  "quartiers": [<liste de quartiers mentionnés>],\n'
            '  "description_libre": "<résumé des souhaits en 1 phrase>"\n'
            '}'
        )
        try:
            extract_model = genai.GenerativeModel(
                _EXTRACT_MODEL,   # gemini-1.5-flash : extraction rapide
                generation_config=genai.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=300,
                    response_mime_type="application/json",
                ),
            )
            raw = extract_model.generate_content(extraction_prompt).text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            profil_detecte = json.loads(raw)
        except Exception as e:
            logger.warning("Extraction profil échouée : %s", e)

        # ── 2. Recherche ChromaDB avec filtres extraits ───────────────────────
        query_parts = [req.question]
        if profil_detecte.get("intention") == "rs":
            query_parts.append("vue mer résidence secondaire plage")
        elif profil_detecte.get("intention") == "investissement":
            query_parts.append("rendement locatif studio T2 centre")
        if profil_detecte.get("quartiers"):
            query_parts.extend(profil_detecte["quartiers"])
        query = " ".join(query_parts)

        filtre = _build_chroma_filters(
            profil_detecte.get("budget_max"),
            profil_detecte.get("surface_min"),
            profil_detecte.get("nb_pieces_min"),
            profil_detecte.get("type_bien"),
        )
        biens = search_similar(query=query, n_results=req.n_context, filtre_meta=filtre)

    # ── 3. Contexte biens + construction du message Gemini ────────────────────
    if _is_fiche:
        # Analyse directe : le prompt contient déjà toutes les données du bien
        system_chat = (
            "Tu es NidBuyer, expert en immobilier à Toulon. "
            "Analyse le bien décrit avec précision, structure ta réponse en markdown. "
            "Sois factuel, chiffré, et adapte ton conseil au profil de l'acheteur. "
            "Va directement à l'analyse sans préambule ni formule de politesse."
        )
        gemini_history: list[dict] = []
        user_msg = req.question   # le prompt fiche_decision_v3 complet
    else:
        ctx_lines: list[str] = []
        for i, b in enumerate(biens, 1):
            pm2 = ""
            if b.get("prix") and b.get("surface") and b["surface"] > 0:
                pm2 = f" ({b['prix'] / b['surface']:.0f} €/m²)"
            ctx_lines.append(
                f"Bien #{i} — {b.get('titre', 'N/A')}\n"
                f"  Quartier : {b.get('quartier', '?')} | "
                f"Prix : {b.get('prix', '?')} €{pm2} | "
                f"Surface : {b.get('surface', '?')} m² | "
                f"Pièces : {b.get('nb_pieces', '?')} | DPE : {b.get('dpe', '?')}\n"
                f"  {str(b.get('document', ''))[:200]}"
            )
        ctx = "\n\n".join(ctx_lines) if ctx_lines else "Aucun bien trouvé pour cette requête."

        system_chat = (
            "TU ES UN CONSEILLER IMMOBILIER, PAS UN CHERCHEUR. "
            "Ne produis aucun texte avant la balise <ANSWER>. "
            "Tu es NidBuyer, conseiller immobilier expert à Toulon. "
            "Tu accompagnes l'acheteur de façon personnalisée et chaleureuse. "
            "Si tu ne connais pas encore le profil, pose 1 question ciblée "
            "(budget ? usage ? quartier préféré ?). "
            "Si tu as des biens en contexte, présente le(s) plus pertinent(s) "
            "avec des chiffres précis. "
            "Tu te bases UNIQUEMENT sur les biens fournis — jamais de données inventées. "
            "Sois concis (max 3 paragraphes). "
            "RÈGLE ABSOLUE : ta réponse doit commencer IMMÉDIATEMENT par <ANSWER> "
            "et se terminer par </ANSWER>. Rien avant, rien après. "
            "Exemple : <ANSWER>Bonjour ! Voici ce que j'ai trouvé…</ANSWER>"
        )
        gemini_history = []
        for m in req.history[-6:]:
            role = "model" if m.role == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [m.content]})

        profil_resume = profil_detecte.get("description_libre") or "À préciser"
        user_msg = (
            f"Biens disponibles dans la base NidBuyer :\n{ctx}\n\n"
            f"Profil détecté : {profil_resume}\n"
            f"Question : {req.question}\n\n"
            "Rappel : entoure ta réponse de <ANSWER>…</ANSWER>."
        )

    # ── 4. Réponse Gemini ─────────────────────────────────────────────────────
    reponse_text = "Je rencontre une difficulté momentanée. Réessayez dans quelques instants."
    try:
        chat_model = genai.GenerativeModel(
            _CHAT_MODEL,
            system_instruction=system_chat,
            generation_config=genai.GenerationConfig(
                max_output_tokens=800,
                temperature=0.3 if _is_fiche else 0.7,
                stop_sequences=[] if _is_fiche else ["Input:", "Reasoning:", "Plan:", "Step 1:", "Goal:"],
            ),
        )
        chat_session = chat_model.start_chat(history=gemini_history)
        raw_text = chat_session.send_message(user_msg).text
        reponse_text = raw_text.strip() if _is_fiche else _clean_llm_output(raw_text)
    except Exception as e:
        logger.error("Gemini chat error : %s", e)

    # ── 5. Formatage des biens pour le frontend ───────────────────────────────
    biens_out = [
        {
            "id":       b.get("id"),
            "titre":    b.get("titre"),
            "quartier": b.get("quartier"),
            "prix":     b.get("prix"),
            "surface":  b.get("surface"),
            "nb_pieces":b.get("nb_pieces"),
            "dpe":      b.get("dpe"),
            "lien":     b.get("lien"),
            "terrasse": b.get("terrasse", 0),
            "balcon":   b.get("balcon", 0),
            "parking":  b.get("parking", 0),
            "distance": b.get("distance"),
        }
        for b in biens
    ]

    return {
        "reponse":          reponse_text,
        "profil_detecte":   profil_detecte,
        "biens_trouves":    biens_out,
        "n_biens_contexte": len(biens),
    }


# ── POST /api/analyse-images ──────────────────────────────────────────────────

@app.post("/api/analyse-images")
def analyse_images(req: AnalyseImagesRequest):
    """
    Analyse vision d'un bien immobilier à partir des URLs de ses photos.
    Toute la logique (téléchargement, prompt, appel Gemini, nettoyage de la sortie)
    est dans vision.llm.evaluate.analyser_bien_par_urls().
    """
    from vision.llm.evaluate import analyser_bien_par_urls

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY manquant — analyse vision désactivée.",
        )

    try:
        return analyser_bien_par_urls(
            urls=req.photos,
            titre=req.titre,
            type_bien=req.type_bien,
            max_images=req.max_images,
        )
    except ValueError as e:
        # Aucune URL exploitable / téléchargements échoués
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Échec côté Gemini
        raise HTTPException(status_code=500, detail=str(e))


# ── Routes stubs (biens individuels) ─────────────────────────────────────────

@app.get("/biens")
def liste_biens(limit: int = 5000):
    """
    Récupère l'ensemble des annonces depuis Supabase (limité à 5000 par défaut).
    Utilisé par le frontend pour générer les statistiques globales du marché.
    """
    from supabase import create_client
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=503, detail="SUPABASE_URL / SUPABASE_KEY manquants")
    try:
        sb = create_client(url, key)
        response = sb.table("annonces").select("*").limit(limit).execute()
        return {"biens": response.data, "total": len(response.data)}
    except Exception as e:
        logger.error("Erreur lors de la récupération de tous les biens: %s", e)
        raise HTTPException(status_code=500, detail="Erreur accès Supabase")


@app.get("/biens/{bien_id}")
def detail_bien(bien_id: str):
    raise HTTPException(status_code=501, detail="Non implémenté")


# ── Alertes ───────────────────────────────────────────────────────────────────

@app.post("/alerte")
def creer_alerte(alerte: AlerteProfil):
    from .alert import sauvegarder_profil
    from .gmail_service import envoyer_email_gmail

    try:
        # Étape 1 : sauvegarde
        sauvegarder_profil(
            email=alerte.email,
            nom_alerte=alerte.nom_alerte,
            profil=alerte.profil.model_dump(),
        )
        logger.info(f"✅ Profil sauvegardé pour {alerte.email}")
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde profil : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde : {str(e)}")

    try:
        # Étape 2 : email de confirmation
        p = alerte.profil
        criteres_html = []
        if p.budget_max:
            criteres_html.append(f"<li><strong>Budget max :</strong> {int(p.budget_max):,} €</li>")
        if p.surface_min:
            criteres_html.append(f"<li><strong>Surface min :</strong> {int(p.surface_min)} m²</li>")
        if p.nb_pieces_min:
            criteres_html.append(f"<li><strong>Pièces min :</strong> {p.nb_pieces_min}</li>")
        if p.quartiers:
            criteres_html.append(f"<li><strong>Communes :</strong> {', '.join(p.quartiers)}</li>")
        if p.description_libre:
            criteres_html.append(f"<li><strong>Mot-clé :</strong> {p.description_libre}</li>")
        criteres_block = (
            "<ul>" + "".join(criteres_html) + "</ul>"
            if criteres_html else "<p><em>Tous les biens disponibles.</em></p>"
        )

        html_confirmation = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2>🏠 NidBuyer — Alerte enregistrée</h2>
                <p>Bonjour,</p>
                <p>Votre alerte <strong>« {alerte.nom_alerte} »</strong> a bien été enregistrée.</p>
                <p>Vous recevrez un email <strong>chaque jour à 9h30</strong> avec les nouveaux biens correspondant à vos critères :</p>
                {criteres_block}
                <hr>
                <p style="font-size: 12px; color: #999;">
                    Email automatique de <strong>NidBuyer</strong> —
                    <a href="https://nidbuyer.aimmo.fr">Gérer vos alertes</a>
                </p>
            </body>
        </html>
        """

        success = envoyer_email_gmail(
            alerte.email,
            "🏠 NidBuyer — Votre alerte a bien été enregistrée",
            html_confirmation,
        )
        if not success:
            logger.warning(f"⚠️ Email non envoyé (retour False) pour {alerte.email}")
    except Exception as e:
        logger.error(f"❌ Erreur envoi Gmail : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur Gmail : {str(e)}")

    return {"status": "ok", "message": f"Alerte enregistrée pour {alerte.email}"}


# ── Admin ─────────────────────────────────────────────────────────────────────
@app.get("/admin/test-gmail")
def test_gmail():
    from .gmail_service import get_gmail_service
    import base64
    from email.mime.text import MIMEText

    # Test 1 : connexion
    try:
        service = get_gmail_service()
        # Force le rafraîchissement du token
        import google.auth.transport.requests
        service._http.credentials.refresh(google.auth.transport.requests.Request())
        token_ok = "✅ Token rafraîchi avec succès"
    except Exception as e:
        return {"etape": "connexion OAuth2", "erreur": str(e)}

    # Test 2 : envoi
    try:
        msg = MIMEText("<p>Test</p>", "html")
        msg["to"] = "projectaimmo@gmail.com"
        msg["from"] = "projectaimmo@gmail.com"
        msg["subject"] = "Test NidBuyer"
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return {"token": token_ok, "envoi": "✅ OK", "message_id": result.get("id")}
    except Exception as e:
        return {"token": token_ok, "envoi": "❌ Échec", "erreur": str(e)}

@app.post("/admin/sync")
def admin_sync(background_tasks: BackgroundTasks, dry_run: bool = False):
    """Déclenche manuellement une synchronisation des annonces en arrière-plan."""
    background_tasks.add_task(sync, dry_run=dry_run)
    return {"status": "sync lancée en arrière-plan", "dry_run": dry_run}


@app.get("/admin/status")
def admin_status():
    """Statut de la base : annonces stockées (Supabase) et indexées (ChromaDB)."""
    from supabase import create_client
    from .rag import _get_client, COLLECTION_NAME

    # Compte ChromaDB sans charger le modèle SentenceTransformer (7s au 1er appel).
    # _get_client() ouvre le SQLite uniquement ; get_collection sans embedding_function
    # est instantané.
    try:
        n_chroma = _get_client().get_collection(COLLECTION_NAME).count()
    except Exception:
        n_chroma = 0  # collection inexistante = 0 annonces indexées

    # Compte Supabase avec timeout strict pour ne pas bloquer si l'URL est fictive.
    def _count_supabase() -> int:
        _url = os.environ.get("SUPABASE_URL", "")
        _key = os.environ.get("SUPABASE_KEY", "")
        sb = create_client(_url, _key)
        return sb.table("annonces").select("id", count="exact").execute().count

    _pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        n_supabase = _pool.submit(_count_supabase).result(timeout=3.0)
    except Exception:
        n_supabase = -1
    finally:
        _pool.shutdown(wait=False)  # ne bloque pas sur le thread Supabase en attente

    last_sync = Path("data/.last_sync")
    ok = n_supabase >= 0 and n_chroma >= 0
    return {
        "supabase_count":   n_supabase,
        "chromadb_count":   n_chroma,
        "annonces_indexees": n_chroma,   # alias pour test_auto_eval.py
        "derniere_sync":    last_sync.read_text() if last_sync.exists() else "jamais",
        "status":           "ok" if ok else "degraded",
    }
