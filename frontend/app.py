"""
NidDouillet by AImmo — Observatoire Immobilier Toulon
Point d'entrée de l'application Streamlit.
"""

import pandas as pd
import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ajout du dossier courant au sys.path pour les imports locaux
_root = str(Path(__file__).parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

load_dotenv(Path(__file__).parent.parent / ".env")

from analysis.regression import (
    compute_dvf_scores,
    compute_multivariate_regression,
    compute_neighborhood_scores,
    compute_regression,
)
from assets.style import inject_css
from config import DVF_CSV_PATH
from data_loader import get_dvf_models, load_data, load_dvf_raw
from ui.tab_analysis import render_analysis
from ui.tab_assistant import render_assistant
from ui.tab_comparator import render_comparator
from ui.tab_list import render_list
from ui.tab_map import render_map
from ui.tab_opportunities import render_opportunities

# ── Config page ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NidDouillet by AImmo — Observatoire Immobilier Toulon",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Données ────────────────────────────────────────────────────────────────────
df_raw     = load_data()
dvf_models = get_dvf_models(str(DVF_CSV_PATH))
df_dvf_raw = load_dvf_raw(str(DVF_CSV_PATH))

# ── Session state — Assistant ──────────────────────────────────────────────────
for _k, _v in [("asst_step", 0), ("asst_type", None),
               ("asst_budget", None), ("asst_surface", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏠 NidDouillet")
    st.markdown(
        '<span style="color:#E8714A;font-size:13px;font-weight:600;letter-spacing:0.3px;">'
        'by AImmo</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("### 🎯 Filtres")

    types_dispo = sorted(df_raw["type_bien"].dropna().unique()) if not df_raw.empty else []
    type_filtre = st.selectbox("Type de bien", ["Tous"] + list(types_dispo))

    budget_max = st.slider("Budget max (€)", 50_000, 500_000, 500_000, 10_000, format="%d €")

    _quartiers_dispo = (
        sorted(df_raw["nom_commune"].dropna().unique().tolist())
        if not df_raw.empty and "nom_commune" in df_raw.columns else []
    )
    quartier_filtre = st.multiselect(
        "📍 Quartier / Commune", options=_quartiers_dispo,
        default=[], placeholder="Tous les quartiers",
    ) if _quartiers_dispo else []

    surface_min = st.number_input("Surface min (m²)", 0, 300, 0, 5)
    pieces_min  = st.number_input("Pièces min",        0, 8,   0, 1)

    sources_dispo = sorted(df_raw["source"].dropna().unique()) if not df_raw.empty else []
    source_filtre = st.selectbox(
        "Source", ["Toutes"] + list(sources_dispo),
        help="Sources actives : PAP · LeBonCoin · SeLoger",
    )

    keyword = st.text_input("🔍 Mot-clé", placeholder="terrasse, parking…")

    prix_baisse_only = st.checkbox("📉 Prix en baisse uniquement")

    st.markdown("---")
    if not df_raw.empty and "date_mutation" in df_raw.columns:
        last_upd = df_raw["date_mutation"].max()
        st.caption("🕐 Dernière mise à jour")
        if pd.notna(last_upd):
            st.markdown(f"**`{last_upd.strftime('%d/%m/%Y %H:%M')}`**")
    st.caption(f"📦 {len(df_raw):,} annonces en base")
    st.markdown("---")
    if st.button("🔄 Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Guard ──────────────────────────────────────────────────────────────────────
if df_raw.empty:
    st.error("⚠️ Aucune donnée disponible. Vérifiez que le scraping a bien tourné.")
    st.stop()

# ── Filtrage ───────────────────────────────────────────────────────────────────
df = df_raw.copy()
if type_filtre != "Tous":
    df = df[df["type_bien"] == type_filtre]
if budget_max < 500_000:
    df = df[df["valeur_fonciere"] <= budget_max]
if surface_min > 0:
    df = df[df["surface_reelle_bati"] >= surface_min]
if pieces_min > 0:
    df = df[df["nombre_pieces_principales"] >= pieces_min]
if source_filtre != "Toutes":
    df = df[df["source"] == source_filtre]
if quartier_filtre and "nom_commune" in df.columns:
    df = df[df["nom_commune"].isin(quartier_filtre)]
if keyword:
    mask_kw = (
        df["description"].fillna("").str.contains(keyword, case=False) |
        df["titre"].fillna("").str.contains(keyword, case=False)
    )
    df = df[mask_kw]
if prix_baisse_only and "prix_baisse" in df.columns:
    df = df[df["prix_baisse"] == True]

# ── Régressions ────────────────────────────────────────────────────────────────
df_scored = (
    compute_regression(df[df["type_bien"].notna()].copy().reset_index(drop=True))
    if not df.empty else pd.DataFrame()
)
if (not df_scored.empty and "ecart_pct" in df_scored.columns
        and "url" in df_scored.columns and "url" in df.columns):
    _reg_cols = df_scored[["url", "ecart_pct", "ecart", "prix_predit"]].dropna(subset=["url"])
    df = df.merge(_reg_cols, on="url", how="left", suffixes=("", "_reg")).reset_index(drop=True)

df_dvf = (
    compute_dvf_scores(df[df["type_bien"].notna()].copy().reset_index(drop=True), models=dvf_models)
    if not df.empty else pd.DataFrame()
)
df_qrt = (
    compute_neighborhood_scores(df[df["type_bien"].notna()].copy().reset_index(drop=True))
    if not df.empty else pd.DataFrame()
)

# ── Header ─────────────────────────────────────────────────────────────────────
last_upd_str = "—"
if not df_raw.empty and "date_mutation" in df_raw.columns:
    lu = df_raw["date_mutation"].max()
    if pd.notna(lu):
        last_upd_str = lu.strftime("%d/%m/%Y à %H:%M")

st.markdown(f"""
<div class="aimmo-header">
  <h1>🏠 Observatoire Immobilier — Toulon — Temps réel</h1>
  <div class="subtitle">
    <span class="badge">≤ 500 000 €</span>
    <span class="badge">PAP · LeBonCoin · SeLoger</span>
    <span>🕐 Mis à jour le {last_upd_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
prix_med = df["valeur_fonciere"].median() if not df.empty and df["valeur_fonciere"].notna().any() else None
surf_med = df["surface_reelle_bati"].median() if not df.empty and df["surface_reelle_bati"].notna().any() else None
pm2_med  = df["prix_m2"].median() if not df.empty and df["prix_m2"].notna().any() else None
delta_nb = len(df) - len(df_raw) if len(df) != len(df_raw) else None

# Delta pm2 : annonces vs DVF (marché réel)
dvf_pm2_delta = None
dvf_pm2_label = None
if pm2_med and not df_dvf_raw.empty and "prix_m2" in df_dvf_raw.columns:
    dvf_pm2 = df_dvf_raw[df_dvf_raw["prix_m2"].notna()]["prix_m2"].median()
    if dvf_pm2 and dvf_pm2 > 0:
        dvf_pm2_delta = round(pm2_med - dvf_pm2)
        dvf_pm2_label = f"{dvf_pm2_delta:+,.0f} € vs DVF"

# Nombre d'opportunités détectées
n_opps = 0
if not df_dvf.empty and "dvf_ecart_pct" in df_dvf.columns:
    n_opps = int((df_dvf["dvf_ecart_pct"] < -10).sum())

k1.metric("📋 Annonces",        f"{len(df):,}",         delta=f"{delta_nb:+}" if delta_nb else None)
k2.metric("💰 Prix médian",     f"{prix_med:,.0f} €"    if prix_med else "—")
k3.metric("📐 Surface médiane", f"{surf_med:.0f} m²"    if surf_med else "—")
k4.metric("💶 Prix/m² médian",  f"{pm2_med:,.0f} €/m²"  if pm2_med else "—",
          delta=dvf_pm2_label, delta_color="inverse")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_analyse, tab_liste, tab_opps, tab_cmp, tab_carte, tab_asst = st.tabs([
    "📊  Marché",
    "📋  Liste des biens",
    "💡  Opportunités",
    "⚖️  Comparateur",
    "🗺️  Carte",
    "🤖  Assistant",
])

with tab_analyse:
    render_analysis(df, df_dvf_raw)

with tab_liste:
    render_list(df)

with tab_opps:
    render_opportunities(df, df_dvf, df_scored, df_qrt)

with tab_cmp:
    render_comparator(df)

with tab_carte:
    # On passe df_dvf (annonces scorées DVF) ou df si pas de scores
    _df_carte = df_dvf if (not df_dvf.empty and "latitude" in df_dvf.columns) else df
    render_map(_df_carte)

with tab_asst:
    render_assistant(df_scored)
