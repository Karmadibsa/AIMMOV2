"""
NidBuyer V2 — Interface Streamlit
Données 100 % API FastAPI locale — aucun CSV.
Design repris de AImmoV1 (CSS, structure, composants).
Profil acheteur déduit par le bot (pas de selectbox fixe).
"""

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Configuration ─────────────────────────────────────────────────────────────

API_URL = "http://localhost:8000"

INTENTIONS = {
    "rp":            "🏡 Résidence Principale",
    "investissement":"📈 Investisseur Locatif",
    "rs":            "🌊 Résidence Secondaire",
    "mixte":         "🏢 Immeuble Mixte",
}

# ── CSS V1 (repris intégralement) ─────────────────────────────────────────────

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #F4F6FA; }

[data-testid="stSidebar"] { background: #1B2B4B !important; color: #CBD5E1 !important; }
[data-testid="stSidebar"] * { color: var(--text-color, #CBD5E1); }
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder { color: #94A3B8 !important; opacity: 1 !important; }
[data-testid="stSidebar"] code { background: #253859 !important; color: #E2E8F0 !important; border: none !important; }
[data-testid="stSidebar"] div, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label { color: #CBD5E1 !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #CBD5E1 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #E8714A !important; }
[data-testid="stSidebar"] input { background: #253859 !important; color: #E2E8F0 !important;
  border-color: #3A5278 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background: #253859 !important;
  border-color: #3A5278 !important; }

[data-baseweb="tab-list"] { display: flex !important; gap: 6px; background: white;
  padding: 8px 10px; border-radius: 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 28px; }
[data-baseweb="tab"] { flex: 1 !important; justify-content: center !important;
  text-align: center !important; border-radius: 10px !important;
  font-weight: 600 !important; font-size: 14px !important;
  color: #64748B !important; padding: 10px 6px !important;
  transition: background 0.15s, color 0.15s !important; }
[aria-selected="true"][data-baseweb="tab"] { background: #1B2B4B !important;
  color: white !important; box-shadow: 0 2px 8px rgba(27,43,75,0.3) !important; }
[aria-selected="true"][data-baseweb="tab"] span,
[aria-selected="true"][data-baseweb="tab"] p { color: white !important; }
[data-baseweb="tab-panel"] { padding-top: 4px !important; }

[data-testid="stButton"] > button { background: #1B2B4B !important; color: white !important;
  border: none !important; border-radius: 10px !important;
  font-weight: 600 !important; padding: 8px 16px !important;
  transition: background 0.15s !important; }
[data-testid="stButton"] > button:hover { background: #2C4A8A !important; }
[data-testid="stButton"] > button p,
[data-testid="stButton"] > button span { color: white !important; }

[data-testid="metric-container"] { background: white; border-radius: 14px;
  padding: 18px 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  border-top: 3px solid #E8714A; }
[data-testid="stMetricLabel"] { color: #64748B !important; font-size: 13px !important; }
[data-testid="stMetricValue"] { color: #1B2B4B !important; font-weight: 700 !important; }

.aimmo-header { background: linear-gradient(135deg, #1B2B4B 0%, #2C4A8A 100%);
  padding: 28px 32px; border-radius: 16px; margin-bottom: 28px;
  box-shadow: 0 6px 24px rgba(27,43,75,0.25); }
.aimmo-header h1 { color: white !important; margin: 0 0 6px 0;
  font-size: 26px; font-weight: 700; }
.aimmo-header .subtitle { color: #93B4D4; font-size: 13px;
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.aimmo-header .badge { background: rgba(255,255,255,0.12); padding: 3px 10px;
  border-radius: 20px; font-size: 12px; color: #BDD4EC; }

.section-card { background: white; border-radius: 14px; padding: 22px 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 20px; }

.profil-card { background: #253859; border-radius: 10px; padding: 12px 14px;
  margin: 8px 0; border-left: 3px solid #E8714A; }
.profil-card .label { color: #94A3B8; font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; }
.profil-card .value { color: #E2E8F0; font-size: 13px; font-weight: 600; }

.badge-opport { background:#DCFCE7; color:#15803D; border:1px solid #86EFAC;
  font-weight:700; font-size:13px; padding:5px 14px; border-radius:8px; display:inline-block; }
.badge-bonne  { background:#D1FAE5; color:#065F46; border:1px solid #6EE7B7;
  font-weight:600; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }
.badge-normal { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;
  font-weight:500; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }
.badge-eleve  { background:#FEF3C7; color:#B45309; border:1px solid #FDE68A;
  font-weight:600; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }

.prix-badge { background: #FFF7ED; border: 1px solid #FED7AA; color: #C2410C !important;
  font-weight: 700; padding: 4px 12px; border-radius: 8px; font-size: 15px; }
.pm2-badge  { background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8 !important;
  font-size: 12px; padding: 2px 8px; border-radius: 6px; }

.result-card { background: white; border-radius: 12px; padding: 14px 18px; margin: 8px 0;
  border-left: 4px solid #E8714A; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.result-card.opport { border-left-color: #16A34A; }
.result-card.bonne  { border-left-color: #22C55E; }
.result-card.normal { border-left-color: #3B82F6; }
.result-card.eleve  { border-left-color: #F59E0B; }

.chat-wrap { max-width: 760px; margin: 0 auto; }
.bien-mini { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;
  padding: 10px 14px; margin: 6px 0; font-size: 13px; }

hr { border: none; border-top: 1px solid #E2E8F0; margin: 16px 0; }
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _badge_html(ecart_pct: float | None) -> str:
    if ecart_pct is None:
        return '<span class="badge-normal">N/A</span>'
    if ecart_pct < -10:
        return f'<span class="badge-opport">🎯 Opportunité &nbsp; {ecart_pct:+.1f} %</span>'
    if ecart_pct < -5:
        return f'<span class="badge-bonne">✅ Bonne affaire &nbsp; {ecart_pct:+.1f} %</span>'
    if ecart_pct <= 5:
        return f'<span class="badge-normal">Prix marché &nbsp; {ecart_pct:+.1f} %</span>'
    return f'<span class="badge-eleve">⚠️ Prix élevé &nbsp; {ecart_pct:+.1f} %</span>'


def _bool_icon(val) -> str:
    return "✅" if val else "—"


def _profil_display(profil: dict) -> str:
    intention = profil.get("intention")
    return INTENTIONS.get(intention, "❓ À préciser") if intention else "❓ À préciser"


# ── Appels API ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_status() -> dict:
    try:
        return requests.get(f"{API_URL}/admin/status", timeout=10).json()
    except Exception:
        return {"supabase_count": -1, "chromadb_count": -1, "status": "unreachable"}


def post_chat(question: str, history: list[dict], n_context: int = 5) -> dict:
    """Envoie la question + historique à /api/chat et retourne la réponse complète."""
    try:
        r = requests.post(
            f"{API_URL}/api/chat",
            json={
                "question":  question,
                "history":   history,
                "n_context": n_context,
            },
            timeout=45,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {
            "reponse": "⚠️ API inaccessible — lancez `uvicorn backend.main:app --reload`",
            "profil_detecte": {},
            "biens_trouves": [],
            "n_biens_contexte": 0,
        }
    except Exception as e:
        return {
            "reponse": f"Erreur : {e}",
            "profil_detecte": {},
            "biens_trouves": [],
            "n_biens_contexte": 0,
        }


def fetch_recommendations(profil: dict, n: int) -> dict:
    """Appelle POST /rechercher avec le profil détecté."""
    if not profil.get("intention"):
        return {"recommandations": [], "mediane_m2": None, "n_candidats": 0,
                "error": "Profil incomplet — continuez la conversation avec le bot."}
    try:
        payload = {
            "intention":       profil.get("intention", "rp"),
            "budget_max":      profil.get("budget_max"),
            "surface_min":     profil.get("surface_min"),
            "nb_pieces_min":   profil.get("nb_pieces_min"),
            "quartiers":       profil.get("quartiers", []),
            "description_libre": profil.get("description_libre", ""),
        }
        r = requests.post(f"{API_URL}/rechercher", json=payload, params={"n": n}, timeout=45)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"recommandations": [], "mediane_m2": None, "n_candidats": 0,
                "error": "API inaccessible"}
    except Exception as e:
        return {"recommandations": [], "mediane_m2": None, "n_candidats": 0,
                "error": str(e)}


# ── Setup page ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NidBuyer — Observatoire Immobilier Toulon",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    # Message de bienvenue du bot
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": (
            "Bonjour ! Je suis **NidBuyer**, votre conseiller immobilier IA à Toulon. 🏠\n\n"
            "Pour vous trouver les meilleures opportunités, j'ai besoin de mieux vous connaître :\n"
            "- **Quel est votre projet ?** (résidence principale, investissement locatif, résidence secondaire…)\n"
            "- **Quel est votre budget ?**\n"
            "- **Avez-vous des quartiers ou critères de surface préférés ?**\n\n"
            "Décrivez librement votre projet et je m'occupe du reste !"
        ),
    })

if "detected_profile" not in st.session_state:
    st.session_state.detected_profile: dict = {}

if "n_results" not in st.session_state:
    st.session_state.n_results = 5

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🏠 NidBuyer")
    st.markdown(
        '<span style="color:#E8714A;font-size:13px;font-weight:600;">by AImmo — V2 · Gemini</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Profil détecté (mis à jour par le chat)
    st.markdown("### 🧠 Profil détecté")
    profil = st.session_state.detected_profile

    def _profil_row(label: str, value: str | None) -> None:
        if value:
            st.markdown(
                f'<div class="profil-card">'
                f'<div class="label">{label}</div>'
                f'<div class="value">{value}</div></div>',
                unsafe_allow_html=True,
            )

    _profil_row("Intention",  _profil_display(profil))
    _profil_row("Budget max", f"{profil['budget_max']:,.0f} €".replace(",", " ") if profil.get("budget_max") else None)
    _profil_row("Surface min", f"{profil['surface_min']:.0f} m²" if profil.get("surface_min") else None)
    _profil_row("Nb pièces min", str(profil["nb_pieces_min"]) if profil.get("nb_pieces_min") else None)
    if profil.get("quartiers"):
        _profil_row("Quartiers", ", ".join(profil["quartiers"]))

    if not profil.get("intention"):
        st.caption("_Discutez avec le bot ↗ pour que votre profil soit détecté._")

    st.markdown("---")
    st.markdown("### ⚙️ Paramètres")
    st.session_state.n_results = st.slider("Nombre de recommandations", 3, 20, st.session_state.n_results)

    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.detected_profile = {}
            st.rerun()

    st.markdown("---")
    status = fetch_status()
    sb_ok  = status.get("supabase_count", -1)
    ch_ok  = status.get("chromadb_count", -1)
    dot    = "🟢" if status.get("status") == "ok" else "🔴"
    st.caption(f"{dot} Supabase : **{sb_ok:,}** annonces" if sb_ok >= 0 else f"{dot} Supabase : indisponible")
    st.caption(f"🔵 ChromaDB : **{ch_ok:,}** indexées"   if ch_ok >= 0 else "🔴 ChromaDB : indisponible")

# ── Header ────────────────────────────────────────────────────────────────────

profil_label = _profil_display(st.session_state.detected_profile)
st.markdown(f"""
<div class="aimmo-header">
  <h1>🏠 NidBuyer — Recommandations IA · Toulon</h1>
  <div class="subtitle">
    <span class="badge">{profil_label}</span>
    <span class="badge">Gemini 1.5 Flash + ChromaDB RAG</span>
    <span class="badge">Données temps réel Supabase</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Onglets ───────────────────────────────────────────────────────────────────

tab_asst, tab_opps, tab_carte, tab_statut = st.tabs([
    "🤖  Assistant IA",
    "💡  Opportunités",
    "🗺️  Carte",
    "⚙️  Statut",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASSISTANT IA (entrée principale)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_asst:
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)

    # Affichage historique
    for msg in st.session_state.chat_history:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

            # Affichage compact des biens trouvés (uniquement messages assistant avec biens)
            if msg["role"] == "assistant" and msg.get("biens_trouves"):
                with st.expander(f"📋 {len(msg['biens_trouves'])} bien(s) analysé(s)", expanded=False):
                    for b in msg["biens_trouves"]:
                        prix_str  = f"{b['prix']:,.0f} €".replace(",", " ") if b.get("prix") else "N/C"
                        surf_str  = f"{b.get('surface', '?'):.0f} m²" if b.get("surface") else "?"
                        titre_str = b.get("titre") or "Annonce"
                        lien      = b.get("lien") or ""
                        link_part = f' — [🔗 voir]({lien})' if lien else ""
                        st.markdown(
                            f'<div class="bien-mini"><b>{titre_str}</b><br>'
                            f'📍 {b.get("quartier","?")} &nbsp;|&nbsp; '
                            f'💰 {prix_str} &nbsp;|&nbsp; 📐 {surf_str}'
                            f'{link_part}</div>',
                            unsafe_allow_html=True,
                        )

    # Saisie
    if question := st.chat_input("Décrivez votre projet immobilier…"):
        # Historique sous format API (role/content seulement)
        api_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history
        ]

        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="👤"):
            st.markdown(question)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("NidBuyer réfléchit…"):
                result = post_chat(question, api_history, st.session_state.n_results)

            reponse      = result.get("reponse", "Erreur inattendue.")
            profil_ext   = result.get("profil_detecte", {})
            biens_trouves = result.get("biens_trouves", [])
            n_ctx        = result.get("n_biens_contexte", 0)

            st.markdown(reponse)
            st.caption(f"_Contexte : {n_ctx} bien(s) récupérés depuis ChromaDB_")

            if biens_trouves:
                with st.expander(f"📋 {len(biens_trouves)} bien(s) analysé(s)", expanded=False):
                    for b in biens_trouves:
                        prix_str  = f"{b['prix']:,.0f} €".replace(",", " ") if b.get("prix") else "N/C"
                        surf_str  = f"{b.get('surface', '?'):.0f} m²" if b.get("surface") else "?"
                        titre_str = b.get("titre") or "Annonce"
                        lien      = b.get("lien") or ""
                        link_part = f' — [🔗 voir]({lien})' if lien else ""
                        st.markdown(
                            f'<div class="bien-mini"><b>{titre_str}</b><br>'
                            f'📍 {b.get("quartier","?")} &nbsp;|&nbsp; '
                            f'💰 {prix_str} &nbsp;|&nbsp; 📐 {surf_str}'
                            f'{link_part}</div>',
                            unsafe_allow_html=True,
                        )

        # Mise à jour du profil détecté (fusion conservative)
        if profil_ext:
            current = st.session_state.detected_profile
            # Ne met à jour que les champs nouvellement détectés (pas de régression)
            for key in ("intention", "budget_max", "surface_min", "nb_pieces_min"):
                if profil_ext.get(key) is not None:
                    current[key] = profil_ext[key]
            if profil_ext.get("quartiers"):
                current["quartiers"] = profil_ext["quartiers"]
            if profil_ext.get("description_libre"):
                current["description_libre"] = profil_ext["description_libre"]
            st.session_state.detected_profile = current

        # Sauvegarde avec biens dans l'historique (pour ré-affichage)
        st.session_state.chat_history.append({
            "role":         "assistant",
            "content":      reponse,
            "biens_trouves": biens_trouves,
        })

        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — OPPORTUNITÉS (alimenté par le profil détecté)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_opps:
    current_profil = st.session_state.detected_profile

    if not current_profil.get("intention"):
        st.info(
            "💬 **Commencez par discuter avec le bot** dans l'onglet Assistant — "
            "votre profil sera détecté automatiquement, puis les recommandations apparaîtront ici."
        )
        st.stop()

    with st.spinner("Recherche des meilleures opportunités pour votre profil…"):
        data = fetch_recommendations(current_profil, st.session_state.n_results)

    if "error" in data and not data.get("recommandations"):
        st.error(f"⚠️ {data['error']}")
        st.stop()

    recs       = data.get("recommandations", [])
    mediane_m2 = data.get("mediane_m2")
    n_cand     = data.get("n_candidats", 0)
    df         = pd.DataFrame(recs) if recs else pd.DataFrame()

    # Sous-header
    med_str = f"{mediane_m2:,.0f} €/m²".replace(",", " ") if mediane_m2 else "—"
    st.markdown(
        f'<div class="section-card" style="border-top:3px solid #E8714A;">'
        f'Profil <b>{_profil_display(current_profil)}</b> · '
        f'Médiane : <b>{med_str}</b> · '
        f'<b>{n_cand}</b> candidats analysés</div>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("Aucune recommandation — ChromaDB est peut-être vide. Lancez `python -m backend.rag`.")
        st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    n_opps     = int(df["opportunite"].sum()) if "opportunite" in df.columns else 0
    best_score = df["score"].max()            if "score" in df.columns else None
    best_ecart = df["ecart_pct"].min()        if "ecart_pct" in df.columns else None
    prix_med   = df["prix"].median()          if "prix" in df.columns else None

    k1.metric("🎯 Opportunités",   str(n_opps),
              delta="écart > 10 % sous le marché" if n_opps > 0 else None)
    k2.metric("🏆 Meilleur score", f"{best_score:.0f}/100" if best_score is not None else "—")
    k3.metric("📉 Meilleur écart", f"{best_ecart:+.1f} %"  if best_ecart is not None else "—")
    k4.metric("💰 Prix médian",    f"{prix_med:,.0f} €".replace(",", " ") if prix_med else "—")

    # ── Scatter Prix vs Surface ───────────────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### 📈 Prix vs Surface — score de sous-évaluation")

    df_plot = df.dropna(subset=["surface", "prix", "ecart_pct"]).copy()
    if not df_plot.empty:
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(
            x=df_plot["surface"].tolist(),
            y=df_plot["prix"].tolist(),
            mode="markers",
            marker=dict(
                color=df_plot["ecart_pct"].tolist(),
                colorscale="RdYlGn_r", cmin=-30, cmax=30,
                size=12, opacity=0.85,
                line=dict(width=1, color="white"),
                colorbar=dict(
                    title="Écart (%)",
                    tickvals=[-30, -15, 0, 15, 30],
                    ticktext=["-30 %", "-15 %", "0 %", "+15 %", "+30 %"],
                    thickness=12, len=0.6,
                ),
            ),
            text=df_plot["titre"].fillna("Annonce").tolist(),
            customdata=list(zip(
                df_plot["ecart_pct"].tolist(),
                df_plot.get("prix_m2", pd.Series([0] * len(df_plot))).fillna(0).tolist(),
                df_plot.get("score",   pd.Series([0] * len(df_plot))).fillna(0).tolist(),
                df_plot["quartier"].fillna("").tolist(),
            )),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Surface : %{x:.0f} m²<br>"
                "Prix : %{y:,.0f} €<br>"
                "Prix/m² : %{customdata[1]:,.0f} €/m²<br>"
                "Écart : <b>%{customdata[0]:+.1f} %</b><br>"
                "Score : %{customdata[2]:.0f}/100<br>"
                "Quartier : %{customdata[3]}<extra></extra>"
            ),
        ))
        if mediane_m2 and not df_plot.empty:
            s_min, s_max = df_plot["surface"].min(), df_plot["surface"].max()
            fig_scatter.add_trace(go.Scatter(
                x=[s_min, s_max],
                y=[mediane_m2 * s_min, mediane_m2 * s_max],
                mode="lines",
                name=f"Médiane marché ({mediane_m2:,.0f} €/m²)".replace(",", " "),
                line=dict(color="#1B2B4B", width=2, dash="dash"),
            ))
        fig_scatter.update_layout(
            height=380, margin=dict(t=10, b=10, l=0, r=0),
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis_title="Surface (m²)", yaxis_title="Prix (€)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_scatter.update_yaxes(tickformat=",.0f", ticksuffix=" €")
        st.plotly_chart(fig_scatter, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Bar chart + Tableau ───────────────────────────────────────────────────
    col_bar, col_tbl = st.columns([1, 1], gap="large")

    with col_bar:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🏅 Classement par score")
        df_bar = df.dropna(subset=["score"]).copy().head(15)
        if not df_bar.empty:
            df_bar["label_court"] = df_bar["titre"].fillna("Annonce").str[:35] + "…"
            fig_bar = px.bar(
                df_bar, x="score", y="label_court", orientation="h",
                color="score",
                color_continuous_scale=[[0, "#F87171"], [0.5, "#FBBF24"], [1, "#4ADE80"]],
                range_color=[0, 100],
                text=df_bar["score"].apply(lambda v: f"{v:.0f}"),
                labels={"score": "Score", "label_court": ""},
                template="simple_white",
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                height=420, margin=dict(t=10, b=10, l=0, r=10),
                showlegend=False, coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_tbl:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📋 Tableau des recommandations")
        if not df.empty:
            COLS = {
                "titre": "Titre", "quartier": "Quartier",
                "prix": "Prix (€)", "surface": "Surface (m²)",
                "prix_m2": "€/m²", "ecart_pct": "Écart (%)",
                "score": "Score", "label": "Marché", "lien": "Lien",
            }
            df_tbl = df[[c for c in COLS if c in df.columns]].rename(columns=COLS)
            cfg = {
                "Lien":          st.column_config.LinkColumn("Lien", display_text="🔗"),
                "Prix (€)":      st.column_config.NumberColumn(format="%.0f €"),
                "Surface (m²)":  st.column_config.NumberColumn(format="%.0f m²"),
                "€/m²":          st.column_config.NumberColumn(format="%.0f €/m²"),
                "Écart (%)":     st.column_config.NumberColumn(format="%.1f %%"),
                "Score":         st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
            }
            st.dataframe(df_tbl, use_container_width=True, hide_index=True,
                         column_config=cfg, height=420)

            st.markdown("---")
            buf  = io.BytesIO()
            df_tbl.to_excel(buf, index=False, engine="openpyxl")
            fname = f"nidbuyerv2_{pd.Timestamp.today().strftime('%Y%m%d')}"
            c1, c2, _ = st.columns([1, 1, 2])
            c1.download_button("📊 Excel", data=buf.getvalue(),
                               file_name=f"{fname}.xlsx", use_container_width=True,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            c2.download_button("📄 CSV", data=df_tbl.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"{fname}.csv", use_container_width=True, mime="text/csv")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Fiches détaillées ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔍 Fiches détaillées")

    for i, bien in enumerate(recs):
        titre    = str(bien.get("titre") or "Annonce sans titre")
        prix     = bien.get("prix")
        surface  = bien.get("surface")
        prix_m2  = bien.get("prix_m2")
        ecart_p  = bien.get("ecart_pct")
        score    = bien.get("score")
        quartier = bien.get("quartier") or "—"
        pieces   = bien.get("nb_pieces")
        lien     = bien.get("lien") or ""
        dpe      = bien.get("dpe") or "?"
        avis_ia  = bien.get("avis_ia")

        lbl  = titre[:60]
        lbl += f"  ·  {prix:,.0f} €".replace(",", " ") if prix    else ""
        lbl += f"  ·  {surface:.0f} m²"                if surface else ""
        lbl += f"  ·  {ecart_p:+.1f} %"                if ecart_p is not None else ""
        if i == 0 and avis_ia:
            lbl += "  ·  🤖 Avis IA"

        with st.expander(lbl, expanded=(i == 0)):
            left, right = st.columns([1, 2], gap="medium")

            with left:
                if ecart_p is not None:
                    st.markdown(_badge_html(ecart_p), unsafe_allow_html=True)
                if prix:
                    pm2_str = (
                        f' <span class="pm2-badge">{prix_m2:,.0f} €/m²</span>'.replace(",", " ")
                        if prix_m2 else ""
                    )
                    st.markdown(
                        f'<span class="prix-badge">{prix:,.0f} €</span>{pm2_str}'.replace(",", " "),
                        unsafe_allow_html=True,
                    )
                if score is not None:
                    st.progress(int(score) / 100, text=f"Score NidBuyer : {score:.0f}/100")

                for icon, val in [
                    ("📍 Quartier",  quartier),
                    ("📐 Surface",   f"{surface:.0f} m²" if surface else "—"),
                    ("🚪 Pièces",    f"{int(pieces)}" if pieces else "—"),
                    ("⚡ DPE",       dpe),
                    ("🌿 Terrasse",  _bool_icon(bien.get("terrasse"))),
                    ("🏗️ Travaux",  _bool_icon(bien.get("travaux"))),
                ]:
                    st.markdown(f"**{icon}** : {val}")

                if lien:
                    st.markdown(f"[🔗 Voir l'annonce →]({lien})")

            with right:
                if avis_ia:
                    st.markdown(
                        '<div style="background:#F0F9FF;border:1px solid #BAE6FD;'
                        'border-radius:10px;padding:14px 18px;margin-bottom:12px;">'
                        '<span style="color:#0369A1;font-size:12px;font-weight:600;">'
                        '🤖 Avis NidBuyer IA (Gemini 1.5 Flash)</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(avis_ia)
                else:
                    st.caption("Avis IA disponible uniquement pour la 1ère recommandation.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CARTE
# ═══════════════════════════════════════════════════════════════════════════════

with tab_carte:
    st.markdown("#### 🗺️ Localisation des biens recommandés")

    current_profil = st.session_state.detected_profile
    if not current_profil.get("intention"):
        st.info("Discutez avec le bot pour détecter votre profil, puis revenez ici.")
    else:
        data_carte = fetch_recommendations(current_profil, st.session_state.n_results)
        recs_carte = data_carte.get("recommandations", [])
        df_carte   = pd.DataFrame(recs_carte) if recs_carte else pd.DataFrame()

        if df_carte.empty:
            st.info("Aucune donnée à afficher.")
        else:
            df_geo = df_carte.dropna(subset=["latitude", "longitude"]).copy()
            df_geo = df_geo[(df_geo["latitude"] != 0.0) & (df_geo["longitude"] != 0.0)]

            if df_geo.empty:
                st.info(
                    "Coordonnées GPS non disponibles. Vérifiez que les colonnes "
                    "`latitude`/`longitude` sont renseignées dans Supabase puis relancez "
                    "`python -m backend.rag`."
                )
            else:
                st.caption(f"{len(df_geo)}/{len(df_carte)} biens géolocalisés.")
                st.map(
                    df_geo.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]],
                    zoom=12,
                )
                cols_c = ["titre", "quartier", "prix", "surface", "ecart_pct", "score"]
                st.dataframe(
                    df_geo[[c for c in cols_c if c in df_geo.columns]],
                    use_container_width=True, hide_index=True,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — STATUT
# ═══════════════════════════════════════════════════════════════════════════════

with tab_statut:
    st.markdown("#### ⚙️ Statut du système NidBuyer V2")

    status = fetch_status()
    s_ok   = status.get("status") == "ok"
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "🗄️ Supabase",
        f"{status.get('supabase_count', '?'):,} annonces".replace(",", " ")
        if status.get("supabase_count", -1) >= 0 else "Indisponible",
    )
    col2.metric(
        "🔵 ChromaDB",
        f"{status.get('chromadb_count', '?'):,} indexées".replace(",", " ")
        if status.get("chromadb_count", -1) >= 0 else "Indisponible",
    )
    col3.metric(
        "🕐 Dernière sync",
        str(status.get("derniere_sync", "—"))[:16],
    )

    if s_ok:
        st.success("✅ Tous les services sont opérationnels.")
    else:
        st.error("❌ Un ou plusieurs services sont indisponibles.")

    st.markdown("---")
    st.markdown("**Actions manuelles**")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("▶️ Lancer une sync", use_container_width=True):
            try:
                r = requests.post(f"{API_URL}/admin/sync", timeout=10)
                st.success(r.json().get("status", "Sync lancée"))
            except Exception as e:
                st.error(f"Erreur : {e}")
    with c2:
        st.caption(
            "Déclenche la synchronisation des scrapers en arrière-plan. "
            "Indexation ChromaDB initiale : `python -m backend.rag`"
        )
