"""
Injection du CSS personnalisé dans l'application Streamlit.

Grâce à .streamlit/config.toml (textColor, backgroundColor, primaryColor),
les couleurs de base sont gérées nativement par Streamlit.
Ce CSS ne surcharge que ce que config.toml ne peut pas faire :
  - Sidebar sombre (Streamlit ne supporte pas une sidebar dark en thème light)
  - Tabs full-width avec état actif sombre
  - Boutons dark navy (on veut #1B2B4B, pas l'orange primaryColor)
  - Composants personnalisés (.aimmo-header, .section-card, badges, bulles chat)
"""

import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #F4F6FA; }

/* ══════════════════════════════════════════════════════════════════
   SIDEBAR — fond sombre, texte clair
   (config.toml ne peut pas mettre la sidebar en dark en mode light)
══════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #1B2B4B !important;
    color: #CBD5E1 !important;
}
/* Catch-all : tout élément texte dans la sidebar hérite du texte clair */
[data-testid="stSidebar"] * {
    color: var(--text-color, #CBD5E1);
}
/* Placeholder des inputs sidebar (sinon texte sombre sur fond sombre) */
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {
    color: #94A3B8 !important;
    opacity: 1 !important;
}
/* Inline code dans la sidebar (date de MAJ) : fond sombre cohérent */
[data-testid="stSidebar"] code {
    background: #253859 !important;
    color: #E2E8F0 !important;
    border: none !important;
}
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
[data-testid="stSidebar"] .stSlider [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-baseweb="slider"] [data-testid="stMarkdownContainer"] p { color: #CBD5E1 !important; }

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #CBD5E1 !important; }

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #E8714A !important; }

[data-testid="stSidebar"] input {
    background: #253859 !important; color: #E2E8F0 !important;
    border-color: #3A5278 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #253859 !important; border-color: #3A5278 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="value"],
[data-testid="stSidebar"] [data-baseweb="select"] input { color: #E2E8F0 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="placeholder"] { color: #94A3B8 !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] { background: #3A5278 !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] span { color: #E2E8F0 !important; }
[data-testid="stSidebar"] [data-testid="stTickBarMin"],
[data-testid="stSidebar"] [data-testid="stTickBarMax"] { color: #94A3B8 !important; }

/* ══════════════════════════════════════════════════════════════════
   ONGLETS — 4 boutons pleine largeur + état actif sombre
══════════════════════════════════════════════════════════════════ */
[data-baseweb="tab-list"] {
    display: flex !important;
    gap: 6px;
    background: white;
    padding: 8px 10px;
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    margin-bottom: 28px;
}
[data-baseweb="tab"] {
    flex: 1 !important;
    justify-content: center !important;
    text-align: center !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #64748B !important;
    padding: 10px 6px !important;
    transition: background 0.15s, color 0.15s !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #1B2B4B !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(27,43,75,0.3) !important;
}
/* Texte de l'onglet actif — blanc (config.toml mettrait du dark sinon) */
[aria-selected="true"][data-baseweb="tab"] span,
[aria-selected="true"][data-baseweb="tab"] p { color: white !important; }
[data-baseweb="tab-panel"] { padding-top: 4px !important; }

/* ══════════════════════════════════════════════════════════════════
   BOUTONS — fond sombre (on veut du #1B2B4B, pas l'orange primaryColor)
══════════════════════════════════════════════════════════════════ */
[data-testid="stButton"] > button {
    background: #1B2B4B !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    transition: background 0.15s !important;
}
[data-testid="stButton"] > button:hover { background: #2C4A8A !important; }
[data-testid="stButton"] > button p,
[data-testid="stButton"] > button span { color: white !important; }

/* ══════════════════════════════════════════════════════════════════
   MÉTRIQUES
══════════════════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: white;
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    border-top: 3px solid #E8714A;
}
[data-testid="stMetricLabel"] { color: #64748B !important; font-size: 13px !important; }
[data-testid="stMetricValue"] { color: #1B2B4B !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { color: #64748B !important; }

/* ══════════════════════════════════════════════════════════════════
   COMPOSANTS CUSTOM
══════════════════════════════════════════════════════════════════ */

/* Header */
.aimmo-header {
    background: linear-gradient(135deg, #1B2B4B 0%, #2C4A8A 100%);
    padding: 28px 32px; border-radius: 16px;
    margin-bottom: 28px; box-shadow: 0 6px 24px rgba(27,43,75,0.25);
}
.aimmo-header h1 { color: white !important; margin: 0 0 6px 0; font-size: 26px; font-weight: 700; }
.aimmo-header .subtitle { color: #93B4D4; font-size: 13px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.aimmo-header .badge { background: rgba(255,255,255,0.12); padding: 3px 10px; border-radius: 20px; font-size: 12px; color: #BDD4EC; }

/* Section card */
.section-card {
    background: white; border-radius: 14px; padding: 22px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 20px;
}

/* Tags NLP */
.tag { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; margin: 2px 2px 2px 0; }
.tag-blue   { background: #DBEAFE; color: #1D4ED8; }
.tag-green  { background: #DCFCE7; color: #16A34A; }
.tag-orange { background: #FEF3C7; color: #D97706; }
.tag-sea    { background: #CFFAFE; color: #0E7490; }

/* Badges marché */
.badge-opport { background:#DCFCE7; color:#15803D; border:1px solid #86EFAC; font-weight:700; font-size:13px; padding:5px 14px; border-radius:8px; display:inline-block; }
.badge-bonne  { background:#D1FAE5; color:#065F46; border:1px solid #6EE7B7; font-weight:600; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }
.badge-normal { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE; font-weight:500; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }
.badge-eleve  { background:#FEF3C7; color:#B45309; border:1px solid #FDE68A; font-weight:600; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }

/* Prix badges */
.prix-badge { background: #FFF7ED; border: 1px solid #FED7AA; color: #C2410C !important; font-weight: 700; padding: 4px 12px; border-radius: 8px; font-size: 15px; }
.pm2-badge  { background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8 !important; font-size: 12px; padding: 2px 8px; border-radius: 6px; }

/* Assistant conversationnel */
.chat-wrap { max-width: 680px; margin: 0 auto; padding: 8px 0; }
.bot-bubble {
    background: white; border: 1px solid #E2E8F0;
    border-radius: 18px 18px 18px 4px; padding: 12px 18px;
    margin: 6px 0 10px 0; display: inline-block; max-width: 82%;
    font-size: 14px; color: #1E293B !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05); line-height: 1.5;
}
.user-bubble {
    background: linear-gradient(135deg, #1B2B4B, #2C4A8A);
    border-radius: 18px 18px 4px 18px; padding: 10px 18px;
    display: block; width: fit-content; margin-left: auto;
    font-size: 14px; color: white !important; font-weight: 500;
}
.result-card {
    background: white; border-radius: 12px; padding: 14px 18px;
    margin: 8px 0; border-left: 4px solid #E8714A;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.result-card.opport { border-left-color: #16A34A; }
.result-card.bonne  { border-left-color: #22C55E; }
.result-card.normal { border-left-color: #3B82F6; }
.result-card.eleve  { border-left-color: #F59E0B; }

hr { border: none; border-top: 1px solid #E2E8F0; margin: 16px 0; }
"""


def inject_css() -> None:
    """Injecte le CSS personnalisé dans la page Streamlit."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
