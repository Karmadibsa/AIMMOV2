"""Onglet 3 — Opportunités (régression linéaire prix ~ surface)."""

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import DVF_REGRESSION
from ui.components import market_badge_html, photo_carousel, tags_html

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Transforme les colonnes de l'API V2 au format attendu par la V1."""
    if df is None or df.empty:
        return df
    
    df_norm = df.copy()
    mapping = {
        "prix": "valeur_fonciere",
        "surface": "surface_reelle_bati",
        "pieces": "nombre_pieces_principales",
        "quartier": "nom_commune",
        "lien": "url",
    }
    df_norm.rename(columns=mapping, inplace=True)
    
    if "surface_reelle_bati" in df_norm.columns and "valeur_fonciere" in df_norm.columns:
        mask = df_norm["surface_reelle_bati"].fillna(0) > 0
        if "prix_m2" not in df_norm.columns:
            df_norm["prix_m2"] = float("nan")
        df_norm.loc[mask, "prix_m2"] = (df_norm.loc[mask, "valeur_fonciere"] / df_norm.loc[mask, "surface_reelle_bati"]).round(0)
    
    return df_norm

def render_opportunities(
    df: pd.DataFrame,
    df_dvf: pd.DataFrame,
    df_scored: pd.DataFrame,
    df_qrt: pd.DataFrame | None = None,
) -> None:
    df = normalize_df(df)
    df_dvf = normalize_df(df_dvf)
    df_scored = normalize_df(df_scored)
    if df_qrt is not None:
        df_qrt = normalize_df(df_qrt)

    # ── Sélecteur de méthode ─────────────────────────────────────────────────
    col_meth, _ = st.columns([3, 2])
    with col_meth:
        methode = st.radio(
            "Référence d'évaluation",
            ["📚 DVF historique", "📊 Dynamique — annonces actuelles", "📍 Par quartier (−1.5 σ)"],
            index=0,
            horizontal=True,
        )
    use_dvf = "DVF" in methode
    use_qrt = "quartier" in methode

    # Alias selon la méthode choisie
    if use_dvf:
        _df_ref, _col_ep, _col_e, _col_pp = df_dvf, "dvf_ecart_pct", "dvf_ecart", "dvf_prix_predit"
        _col_slope, _col_inter = "_dvf_slope", "_dvf_intercept"
    elif use_qrt:
        _df_ref = df_qrt if df_qrt is not None and not df_qrt.empty else df_scored
        _col_ep, _col_e, _col_pp = "qrt_ecart_pct", "qrt_ecart", "qrt_prix_predit"
        _col_slope, _col_inter = None, None  # pas de droite de régression pour la méthode quartier
    else:
        _df_ref, _col_ep, _col_e, _col_pp = df_scored, "ecart_pct", "ecart", "prix_predit"
        _col_slope, _col_inter = "_slope", "_intercept"

    if _df_ref.empty or _col_ep not in _df_ref.columns:
        st.info("😕 Pas assez de données pour calculer la régression.")
        return

    # ── Info Quartier ─────────────────────────────────────────────────────────
    if use_qrt:
        n_qrt = _df_ref["nom_commune"].nunique() if "nom_commune" in _df_ref.columns else 0
        st.markdown(f"""
        <div class="section-card" style="border-top:3px solid #0E7490;">
        <strong>📍 Méthode par quartier</strong> — Seuil : prix/m² &lt; moyenne quartier − 1.5×σ.<br>
        Calcul <strong>from scratch</strong> (pur Python) sur <strong>{n_qrt} quartiers</strong> détectés.
        Un bien est "Opportunité" s'il est statistiquement sous-évalué dans son propre secteur géographique.
        </div>
        """, unsafe_allow_html=True)

    # ── Info DVF uniquement ──────────────────────────────────────────────────
    if use_dvf:
        _n_app, _n_mais = DVF_REGRESSION["Appartement"]["n"], DVF_REGRESSION["Maison"]["n"]
        _r2_app, _r2_mais = DVF_REGRESSION["Appartement"]["r2"], DVF_REGRESSION["Maison"]["r2"]
        _sl_app, _sl_mais = DVF_REGRESSION["Appartement"]["slope"], DVF_REGRESSION["Maison"]["slope"]
        st.markdown(f"""
        <div class="section-card" style="border-top:3px solid #8B5CF6;">
        <strong>📚 Référence DVF historique</strong> — Prix comparé à
        <strong>{_n_app + _n_mais:,} ventes réelles</strong> enregistrées à Toulon
        (DVF 2024-2025, source DGFiP).<br>
        Modèles : Appartement = <b>{_sl_app:,.0f} €/m²</b> (n={_n_app:,}, R²={_r2_app})
        &nbsp;|&nbsp; Maison = <b>{_sl_mais:,.0f} €/m²</b> (n={_n_mais:,}, R²={_r2_mais})<br>
        </div>
        """, unsafe_allow_html=True)

    # ── Opportunités = écart < -10 % ──────────────────────────────────────────
    df_opps  = _df_ref[_df_ref[_col_ep] < -10].sort_values(_col_ep)
    n_opps   = len(df_opps)
    econ_med = df_opps[_col_e].median() if n_opps > 0 else None
    best_row = df_opps.iloc[0] if n_opps > 0 else None

    # ── KPIs ──────────────────────────────────────────────────────────────────
    ko1, ko2, ko3 = st.columns(3)
    ko1.metric("🎯 Opportunités détectées", f"{n_opps}", delta="écart > 10 % sous le marché")
    if best_row is not None and pd.notna(best_row[_col_ep]):
        ko2.metric("🏆 Meilleure affaire",
                   f"{best_row[_col_ep]:.1f} %",
                   delta=f"{best_row[_col_e]:,.0f} € sous le marché")
    else:
        ko2.metric("🏆 Meilleure affaire", "—")

    # ── Scatter + droite de régression ───────────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### 📈 Prix vs Surface — avec droite de régression")

    COLORS_TYPE = {"Appartement": "#E8714A", "Maison": "#1B2B4B"}
    fig_reg = go.Figure()

    for ttype, grp in _df_ref.groupby("type_local"):
        c = COLORS_TYPE.get(ttype, "#8B5CF6")
        _dropna_cols = [col for col in [_col_slope, _col_inter, "surface_reelle_bati", "valeur_fonciere"] if col is not None]
        grp_valid = grp.dropna(subset=_dropna_cols)
        if grp_valid.empty:
            continue

        fig_reg.add_trace(go.Scatter(
            x=grp_valid["surface_reelle_bati"].tolist(),
            y=grp_valid["valeur_fonciere"].tolist(),
            mode="markers",
            name=ttype,
            marker=dict(
                color=grp_valid[_col_ep].tolist(),
                colorscale="RdYlGn_r", cmin=-30, cmax=30,
                size=8, opacity=0.75, line=dict(width=0), showscale=False,
            ),
            text=grp_valid["titre"].fillna("").tolist(),
            customdata=list(zip(
                grp_valid[_col_ep].tolist(),
                grp_valid[_col_e].fillna(0).tolist(),
                grp_valid[_col_pp].fillna(0).tolist(),
            )),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Surface : %{x:.0f} m²<br>"
                "Prix réel : %{y:,.0f} €<br>"
                "Prix attendu : %{customdata[2]:,.0f} €<br>"
                "Écart : <b>%{customdata[0]:.1f} %</b> (%{customdata[1]:+,.0f} €)"
                "<extra>" + ttype + "</extra>"
            ),
        ))
        if _col_slope and _col_inter and _col_slope in grp_valid.columns:
            slope     = float(grp_valid[_col_slope].iloc[0])
            intercept = float(grp_valid[_col_inter].iloc[0])
            x_min     = float(grp_valid["surface_reelle_bati"].min())
            x_max     = float(grp_valid["surface_reelle_bati"].max())
            fig_reg.add_trace(go.Scatter(
                x=[x_min, x_max],
                y=[slope * x_min + intercept, slope * x_max + intercept],
                mode="lines",
                name=f"Tendance {ttype}" + (" (DVF)" if use_dvf else ""),
                line=dict(color=c, width=2, dash="dash"),
            ))

    fig_reg.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(
            colorscale="RdYlGn_r", cmin=-30, cmax=30, color=[0], showscale=True,
            colorbar=dict(
                title="Écart (%)", tickvals=[-30, -15, 0, 15, 30],
                ticktext=["-30 %", "-15 %", "0 %", "+15 %", "+30 %"],
                thickness=12, len=0.6,
            ),
        ),
        showlegend=False,
    ))
    fig_reg.update_layout(
        height=380, margin=dict(t=10, b=10, l=0, r=0),
        paper_bgcolor="white", plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
        xaxis_title="Surface (m²)", yaxis_title="Prix (€)",
    )
    fig_reg.update_yaxes(tickformat=",.0f", ticksuffix=" €")
    st.plotly_chart(fig_reg, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Top 15 + tableau ─────────────────────────────────────────────────────
    col_bar, col_tbl = st.columns([1, 1], gap="large")

    with col_bar:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🏅 Top 15 meilleures affaires")
        top15 = df_opps.head(15).copy()
        if not top15.empty:
            top15["label"] = top15["titre"].fillna("Annonce").str[:35] + "…"
            fig_bar = px.bar(
                top15, x=_col_ep, y="label", orientation="h",
                color=_col_ep, color_continuous_scale="RdYlGn_r", range_color=[-40, 0],
                text=top15[_col_ep].apply(lambda v: f"{v:.1f} %"),
                labels={_col_ep: "Écart (%)", "label": ""}, template="simple_white",
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                height=420, margin=dict(t=10, b=10, l=0, r=10),
                paper_bgcolor="white", plot_bgcolor="white",
                showlegend=False, coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Aucune opportunité détectée avec les filtres actuels.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_tbl:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📋 Tableau des opportunités")
        if not df_opps.empty:
            COLS_OPP = {
                "titre": "Titre", "type_local": "Type",
                "valeur_fonciere": "Prix réel (€)", _col_pp: "Prix attendu (€)",
                _col_e: "Économie (€)", _col_ep: "Écart (%)",
                "surface_reelle_bati": "Surface (m²)", "url": "Lien",
            }
            df_tbl = (
                df_opps[[c for c in COLS_OPP if c in df_opps.columns]]
                .rename(columns=COLS_OPP)
            )
            st.dataframe(
                df_tbl, use_container_width=True, hide_index=True,
                column_config={
                    "Lien":             st.column_config.LinkColumn("Lien", display_text="🔗 Voir"),
                    "Titre":            st.column_config.TextColumn("Titre", width="medium"),
                    "Prix réel (€)":    st.column_config.NumberColumn(format="%.0f €"),
                    "Prix attendu (€)": st.column_config.NumberColumn(format="%.0f €"),
                    "Économie (€)":     st.column_config.NumberColumn(format="%.0f €"),
                    "Écart (%)":        st.column_config.NumberColumn(format="%.1f %%"),
                    "Surface (m²)":     st.column_config.NumberColumn(format="%.0f m²"),
                },
                height=420,
            )
        else:
            st.info("Aucune opportunité pour les filtres actuels.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────────────
    if not df_opps.empty:
        st.markdown("---")
        st.markdown("#### 📥 Exporter les opportunités du jour")
        _export_cols = {
            "titre": "Titre", "type_local": "Type",
            "valeur_fonciere": "Prix réel (€)", _col_pp: "Prix attendu (€)",
            _col_e: "Économie (€)", _col_ep: "Écart (%)",
            "surface_reelle_bati": "Surface (m²)",
            "nombre_pieces_principales": "Pièces",
            "nom_commune": "Commune", "source": "Source", "url": "Lien",
        }
        _df_export = (
            df_opps[[c for c in _export_cols if c in df_opps.columns]]
            .copy().rename(columns=_export_cols)
        )
        _fname = f"opportunites_toulon_{pd.Timestamp.today().strftime('%Y%m%d')}"
        _col_ex1, _col_ex2, _ = st.columns([1, 1, 3])
        with _col_ex1:
            _buf = io.BytesIO()
            _df_export.to_excel(_buf, index=False, engine="openpyxl")
            st.download_button(
                label="📊 Télécharger Excel", data=_buf.getvalue(),
                file_name=f"{_fname}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with _col_ex2:
            st.download_button(
                label="📄 Télécharger CSV",
                data=_df_export.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{_fname}.csv", mime="text/csv",
                use_container_width=True,
            )

    # ── Fiches détaillées ─────────────────────────────────────────────────────
    if not df_opps.empty:
        st.markdown("---")
        st.markdown("#### 🔍 Fiches détaillées — Meilleures opportunités")
        for _, row in df_opps.head(20).iterrows():
            titre   = str(row.get("titre", "Annonce sans titre"))
            prix    = row.get("valeur_fonciere")
            surface = row.get("surface_reelle_bati")
            pm2     = row.get("prix_m2")
            ecart_p = row.get(_col_ep)
            ecart_e = row.get(_col_e)
            tags    = row.get("tags", [])
            source  = str(row.get("source", "")).upper()

            lbl = titre
            if pd.notna(prix):    lbl += f"  ·  {prix:,.0f} €"
            if pd.notna(surface): lbl += f"  ·  {surface:.0f} m²"
            if pd.notna(ecart_p): lbl += f"  ·  🟢 {ecart_p:.1f} %"

            with st.expander(lbl):
                left, right = st.columns([1, 2], gap="medium")
                with left:
                    if pd.notna(ecart_p):
                        st.markdown(market_badge_html(float(ecart_p)), unsafe_allow_html=True)
                        if pd.notna(ecart_e):
                            prix_p = row.get(_col_pp)
                            st.markdown(
                                f'<div style="background:#F0FDF4;border:1px solid #BBF7D0;'
                                f'border-radius:8px;padding:6px 12px;margin:6px 0;">'
                                f'<span style="color:#475569;font-size:12px;">'
                                f'Prix attendu : <b>{prix_p:,.0f} €</b><br>'
                                f'💰 Économie : <b>{abs(ecart_e):,.0f} €</b></span></div>',
                                unsafe_allow_html=True,
                            )
                    if pd.notna(prix):
                        st.markdown(
                            f'<span class="prix-badge">{prix:,.0f} €</span>'
                            + (f' <span class="pm2-badge">{pm2:,.0f} €/m²</span>' if pd.notna(pm2) else ""),
                            unsafe_allow_html=True,
                        )
                    for icon_lbl, val in [
                        ("🏷️ Source",  source),
                        ("🏠 Type",    row.get("type_local", "—")),
                        ("📐 Surface", f"{surface:.0f} m²" if pd.notna(surface) else "—"),
                        ("🚪 Pièces",  f"{int(row['nombre_pieces_principales'])}"
                         if pd.notna(row.get("nombre_pieces_principales")) else "—"),
                        ("📍 Commune", row.get("nom_commune", "—")),
                    ]:
                        st.markdown(f"**{icon_lbl}** : {val}")
                    url = row.get("url")
                    if pd.notna(url) and url:
                        st.markdown(f"[🔗 Voir l'annonce →]({url})")
                with right:
                    # Carousel photos
                    _photos_raw = row.get("photos")
                    if _photos_raw is not None:
                        _opp_key = str(row.get("url", _))
                        photo_carousel(_photos_raw, key=f"opp_{_opp_key}")

                    if tags:
                        st.markdown(tags_html(tags), unsafe_allow_html=True)
                    desc = str(row.get("description", "")).strip()
                    if desc and desc != "nan":
                        st.markdown(
                            f"<small style='color:#475569;line-height:1.6'>"
                            f"{desc[:700]}{'…' if len(desc) > 700 else ''}</small>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption("Pas de description disponible.")
