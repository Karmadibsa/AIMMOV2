"""Onglet 1 — Analyse de marché (graphiques)."""

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_BG = "rgba(0,0,0,0)"  # fond transparent pour les graphiques dans st.container

# ── Stats from scratch (pas de numpy) ─────────────────────────────────────────

def _mean(xs: list) -> float:
    return sum(xs) / len(xs) if xs else 0.0

def _median(xs: list) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 != 0 else (s[mid - 1] + s[mid]) / 2

def _std(xs: list) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def render_analysis(df: pd.DataFrame, df_dvf: pd.DataFrame | None = None) -> None:
    col_l, col_r = st.columns(2, gap="medium")

    # ── 1. Types de biens (Pie) ──────────────────────────────────────────────
    with col_l:
        with st.container(border=True):
            st.markdown("#### 🏠 Types de biens")
            if not df.empty:
                typ = df["type_local"].value_counts().reset_index()
                typ.columns = ["Type", "Annonces"]
                fig = px.pie(
                    typ, names="Type", values="Annonces",
                    color="Type",
                    color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                    hole=0.5,
                )
                fig.update_layout(
                    height=280, margin=dict(t=10, b=10, l=0, r=0),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    paper_bgcolor=_BG,
                )
                fig.update_traces(textinfo="percent+label", textfont_size=13)
                st.plotly_chart(fig, use_container_width=True)

    # ── 2. Distribution des prix (Histogramme) ───────────────────────────────
    with col_r:
        with st.container(border=True):
            st.markdown("#### 📊 Distribution des prix")
            df_h = df.dropna(subset=["valeur_fonciere"])
            if not df_h.empty:
                fig = px.histogram(
                    df_h, x="valeur_fonciere", nbins=20, color="type_local",
                    color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                    labels={"valeur_fonciere": "Prix (€)", "type_local": "Type", "count": "Annonces"},
                    template="simple_white",
                )
                fig.update_layout(
                    height=280, margin=dict(t=10, b=10, l=0, r=0),
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    bargap=0.1, legend_title_text="",
                    legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
                )
                fig.update_xaxes(tickformat=",.0f", ticksuffix=" €")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Pas assez de données.")

    col_l2, col_r2 = st.columns(2, gap="medium")

    # ── 3. Prix vs Surface (Scatter) ─────────────────────────────────────────
    with col_l2:
        with st.container(border=True):
            st.markdown("#### 🔵 Prix en fonction de la surface")
            df_sc = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])
            if not df_sc.empty:
                size_vals = df_sc["prix_m2"].fillna(0).astype(float).tolist()
                fig = px.scatter(
                    df_sc, x="surface_reelle_bati", y="valeur_fonciere",
                    color="type_local", size=size_vals,
                    color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                    hover_name="titre",
                    hover_data={"nombre_pieces_principales": True, "source": True,
                                "prix_m2": ":.0f", "surface_reelle_bati": False},
                    labels={"surface_reelle_bati": "Surface (m²)", "valeur_fonciere": "Prix (€)",
                            "type_local": "Type", "prix_m2": "€/m²"},
                    template="simple_white", opacity=0.8,
                )
                fig.update_layout(
                    height=300, margin=dict(t=10, b=10, l=0, r=0),
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    legend_title_text="",
                    legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
                )
                fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Pas assez de données.")

    # ── 4. Distribution par nombre de pièces ──────────────────────────────────
    with col_r2:
        with st.container(border=True):
            st.markdown("#### 🚪 Distribution par nombre de pièces")
            df_pc = df.dropna(subset=["nombre_pieces_principales"])
            if not df_pc.empty:
                df_pc = df_pc.copy()
                df_pc["pieces_label"] = df_pc["nombre_pieces_principales"].astype(int).apply(
                    lambda x: f"T{x}" if 1 <= x <= 5 else ("T6+" if x > 5 else "N/A")
                )
                ordre = ["T1", "T2", "T3", "T4", "T5", "T6+"]
                counts = (
                    df_pc["pieces_label"].value_counts()
                    .reindex([o for o in ordre if o in df_pc["pieces_label"].unique()])
                    .reset_index()
                )
                counts.columns = ["Type", "Annonces"]
                fig = px.bar(
                    counts, x="Type", y="Annonces",
                    color="Type",
                    color_discrete_sequence=["#93B4D4", "#6B94BF", "#4A7DAA", "#2C4A8A",
                                             "#1B2B4B", "#E8714A"],
                    text="Annonces", template="simple_white",
                )
                fig.update_traces(textposition="outside", marker_line_width=0)
                fig.update_layout(
                    height=300, margin=dict(t=20, b=10, l=0, r=0),
                    showlegend=False, paper_bgcolor=_BG, plot_bgcolor=_BG,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Pas assez de données.")

    # ── 5. Analyse de régression — au choix ──────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 📈 Analyse de régression")
        reg_mode = st.radio(
            "Type d'analyse",
            [
                "📈 Régression linéaire (Prix ~ Surface)",
                "📍 Prix/m² moyen par quartier",
                "📊 Régression multivariée (Surface + Pièces + DPE)",
            ],
            horizontal=True,
            key="reg_mode_select",
        )

        df_reg = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])

        if "Linéaire" in reg_mode:
            fig_lr = go.Figure()
            COLS = {"Appartement": "#E8714A", "Maison": "#1B2B4B"}
            for ttype, grp in df_reg.groupby("type_local"):
                c = COLS.get(ttype, "#8B5CF6")
                xs = grp["surface_reelle_bati"].tolist()
                ys = grp["valeur_fonciere"].tolist()
                fig_lr.add_trace(go.Scatter(
                    x=xs, y=ys, mode="markers", name=ttype,
                    marker=dict(color=c, size=5, opacity=0.6),
                    text=grp["titre"].fillna("").tolist(),
                    hovertemplate="<b>%{text}</b><br>%{x:.0f} m² → %{y:,.0f} €<extra>" + ttype + "</extra>",
                ))
                if len(xs) >= 2:
                    n = len(xs)
                    xm = sum(xs) / n
                    ym = sum(ys) / n
                    denom = sum((x - xm) ** 2 for x in xs)
                    if denom > 0:
                        slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom
                        intercept = ym - slope * xm
                        x_min, x_max = min(xs), max(xs)
                        fig_lr.add_trace(go.Scatter(
                            x=[x_min, x_max],
                            y=[slope * x_min + intercept, slope * x_max + intercept],
                            mode="lines", name=f"Tendance {ttype}",
                            line=dict(color=c, width=2, dash="dash"),
                        ))
            fig_lr.update_layout(
                height=360, margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor=_BG, plot_bgcolor=_BG,
                xaxis_title="Surface (m²)", yaxis_title="Prix (€)",
                legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
            )
            fig_lr.update_yaxes(tickformat=",.0f", ticksuffix=" €")
            st.plotly_chart(fig_lr, use_container_width=True)

        elif "quartier" in reg_mode:
            col_qrt = "nom_commune" if "nom_commune" in df.columns else "quartier"
            df_qrt_chart = (
                df.dropna(subset=["prix_m2", col_qrt])
                .groupby(col_qrt)["prix_m2"]
                .agg(["median", "count"])
                .reset_index()
                .rename(columns={"median": "Prix/m² médian", "count": "N annonces"})
            )
            df_qrt_chart = df_qrt_chart[df_qrt_chart["N annonces"] >= 3].sort_values("Prix/m² médian", ascending=True)
            if not df_qrt_chart.empty:
                fig_qrt = px.bar(
                    df_qrt_chart, x="Prix/m² médian", y=col_qrt, orientation="h",
                    color="Prix/m² médian", color_continuous_scale="RdYlGn_r",
                    text=df_qrt_chart["Prix/m² médian"].apply(lambda v: f"{v:,.0f} €/m²"),
                    labels={"Prix/m² médian": "€/m² médian", col_qrt: "Quartier"},
                    template="simple_white",
                )
                fig_qrt.update_traces(textposition="outside")
                fig_qrt.update_layout(
                    height=max(300, len(df_qrt_chart) * 30), margin=dict(t=10, b=10, l=0, r=10),
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    showlegend=False, coloraxis_showscale=False,
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig_qrt, use_container_width=True)
            else:
                st.info("Pas assez de données par quartier (minimum 3 annonces).")

        else:
            try:
                from analysis.regression import compute_multivariate_regression
                with st.spinner("Calcul de la régression multivariée (descente de gradient)…"):
                    df_mv = compute_multivariate_regression(df_reg)

                dpe_coverage = (
                    df_reg["dpe"].notna().sum() / len(df_reg) * 100
                    if "dpe" in df_reg.columns and len(df_reg) > 0 else 0.0
                )
                dpe_used = dpe_coverage > 30.0
                dpe_icon = "✅" if dpe_used else "⚠️"
                st.caption(
                    f"**Modèle** : Surface + Pièces"
                    + (f" + DPE  {dpe_icon} (couverture DPE : {dpe_coverage:.0f} %)"
                       if dpe_used else
                       f" *(DPE exclu — couverture insuffisante : {dpe_coverage:.0f} %)*")
                    + "  ·  Algorithme : descente de gradient (from scratch, sans bibliothèque ML)"
                )

                fig_mv = go.Figure()
                COLS = {"Appartement": "#E8714A", "Maison": "#1B2B4B"}
                for ttype, grp in df_mv.dropna(subset=["mv_prix_predit"]).groupby("type_local"):
                    c = COLS.get(ttype, "#8B5CF6")
                    r2 = grp["mv_r2"].iloc[0] if "mv_r2" in grp.columns else None
                    r2_lbl = f" (R²={r2:.3f})" if r2 is not None else ""
                    fig_mv.add_trace(go.Scatter(
                        x=grp["surface_reelle_bati"].tolist(),
                        y=grp["valeur_fonciere"].tolist(),
                        mode="markers", name=f"{ttype}{r2_lbl}",
                        marker=dict(
                            color=grp["mv_ecart_pct"].tolist(),
                            colorscale="RdYlGn_r", cmin=-30, cmax=30,
                            size=6, opacity=0.7, showscale=False,
                        ),
                        text=grp["titre"].fillna("").tolist(),
                        hovertemplate="<b>%{text}</b><br>%{x:.0f} m² → %{y:,.0f} €<extra>" + ttype + r2_lbl + "</extra>",
                    ))
                    grp_tend = grp.dropna(subset=["surface_reelle_bati", "mv_prix_predit"]).sort_values("surface_reelle_bati")
                    if len(grp_tend) >= 2:
                        x_tend = [float(grp_tend["surface_reelle_bati"].iloc[0]),
                                   float(grp_tend["surface_reelle_bati"].iloc[-1])]
                        y_tend = [float(grp_tend["mv_prix_predit"].iloc[0]),
                                   float(grp_tend["mv_prix_predit"].iloc[-1])]
                        fig_mv.add_trace(go.Scatter(
                            x=x_tend, y=y_tend,
                            mode="lines", name=f"Tendance {ttype} (MV)",
                            line=dict(color=c, width=2, dash="dot"),
                        ))
                fig_mv.update_layout(
                    height=380, margin=dict(t=10, b=10, l=0, r=0),
                    paper_bgcolor=_BG, plot_bgcolor=_BG,
                    xaxis_title="Surface (m²)", yaxis_title="Prix (€)",
                    legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
                )
                fig_mv.update_yaxes(tickformat=",.0f", ticksuffix=" €")
                st.plotly_chart(fig_mv, use_container_width=True)
            except Exception as exc:
                st.warning(f"Régression multivariée non disponible : {exc}")

    # ── 5b. DPE / GES — Distribution & Impact sur le prix ───────────────────
    if "dpe" in df.columns and df["dpe"].notna().sum() >= 5:
        with st.container(border=True):
            st.markdown("#### 🌿 DPE & GES — Performance énergétique des annonces")
            st.caption(
                "Données **officielles** issues directement de l'API BienIci "
                "(DPE obligatoire depuis 2021). Seules les annonces disposant d'un DPE "
                "renseigné à la source sont affichées — aucune valeur n'est inventée."
            )

            DPE_ORDER  = ["A", "B", "C", "D", "E", "F", "G"]
            DPE_COLORS = {
                "A": "#00A651", "B": "#51B747", "C": "#A8CC3B",
                "D": "#FFED00", "E": "#F7931D", "F": "#ED1C24", "G": "#9B1B22",
            }

            col_dpe1, col_dpe2 = st.columns(2, gap="medium")

            with col_dpe1:
                dpe_counts = df["dpe"].value_counts().reindex(DPE_ORDER).dropna().astype(int)
                if not dpe_counts.empty:
                    fig_dpe_dist = go.Figure(go.Bar(
                        x=dpe_counts.index.tolist(),
                        y=dpe_counts.values.tolist(),
                        marker_color=[DPE_COLORS.get(d, "#94A3B8") for d in dpe_counts.index],
                        text=dpe_counts.values.tolist(),
                        textposition="outside",
                    ))
                    fig_dpe_dist.update_layout(
                        title_text="Répartition des classes DPE",
                        height=280, margin=dict(t=40, b=10, l=0, r=0),
                        paper_bgcolor=_BG, plot_bgcolor=_BG,
                        showlegend=False,
                        xaxis_title="Classe DPE", yaxis_title="Annonces",
                    )
                    st.plotly_chart(fig_dpe_dist, use_container_width=True)
                    n_dpe = int(dpe_counts.sum())
                    n_tot = len(df)
                    st.caption(f"📊 {n_dpe} / {n_tot} annonces ({n_dpe/n_tot*100:.0f} %) ont un DPE renseigné.")
                else:
                    st.info("Pas de données DPE disponibles.")

            with col_dpe2:
                df_dpe_prix = df.dropna(subset=["dpe", "prix_m2"])
                df_dpe_prix = df_dpe_prix[df_dpe_prix["prix_m2"] > 0]
                if not df_dpe_prix.empty:
                    rows_dpe = []
                    for classe in DPE_ORDER:
                        vals = [float(v) for v in df_dpe_prix[df_dpe_prix["dpe"] == classe]["prix_m2"].tolist()]
                        if len(vals) < 2:
                            continue
                        sorted_v = sorted(vals)
                        n = len(sorted_v)
                        mid = n // 2
                        med = sorted_v[mid] if n % 2 != 0 else (sorted_v[mid - 1] + sorted_v[mid]) / 2
                        rows_dpe.append({"DPE": classe, "Prix/m² médian": round(med), "N": n})

                    if rows_dpe:
                        fig_dpe_prix = go.Figure(go.Bar(
                            x=[r["DPE"] for r in rows_dpe],
                            y=[r["Prix/m² médian"] for r in rows_dpe],
                            marker_color=[DPE_COLORS.get(r["DPE"], "#94A3B8") for r in rows_dpe],
                            text=[f"{r['Prix/m² médian']:,} €/m²" for r in rows_dpe],
                            textposition="outside",
                            customdata=[[r["N"]] for r in rows_dpe],
                            hovertemplate="Classe %{x}<br>%{y:,.0f} €/m²<br>N=%{customdata[0]}<extra></extra>",
                        ))
                        fig_dpe_prix.update_layout(
                            title_text="Prix/m² médian par classe DPE",
                            height=280, margin=dict(t=40, b=10, l=0, r=0),
                            paper_bgcolor=_BG, plot_bgcolor=_BG,
                            showlegend=False,
                            xaxis_title="Classe DPE", yaxis_title="€/m²",
                        )
                        fig_dpe_prix.update_yaxes(tickformat=",.0f", ticksuffix=" €")
                        st.plotly_chart(fig_dpe_prix, use_container_width=True)
                        st.caption("💡 Les biens A/B sont souvent mieux valorisés ; les passoires thermiques F/G tendent à être décotées.")
                    else:
                        st.info("Pas assez de données DPE par classe (min. 2 annonces).")
                else:
                    st.info("Pas de données DPE avec prix/m² disponibles.")

            # Distribution GES
            if "ges" in df.columns and df["ges"].notna().sum() >= 5:
                st.markdown("---")
                col_ges1, col_ges2 = st.columns(2, gap="medium")
                GES_COLORS = {
                    "A": "#C8E6C9", "B": "#81C784", "C": "#4CAF50",
                    "D": "#AB47BC", "E": "#8E24AA", "F": "#6A1B9A", "G": "#4A148C",
                }
                with col_ges1:
                    ges_counts = df["ges"].value_counts().reindex(DPE_ORDER).dropna().astype(int)
                    if not ges_counts.empty:
                        fig_ges = go.Figure(go.Bar(
                            x=ges_counts.index.tolist(),
                            y=ges_counts.values.tolist(),
                            marker_color=[GES_COLORS.get(g, "#94A3B8") for g in ges_counts.index],
                            text=ges_counts.values.tolist(),
                            textposition="outside",
                        ))
                        fig_ges.update_layout(
                            title_text="Répartition des classes GES (émissions CO₂)",
                            height=260, margin=dict(t=40, b=10, l=0, r=0),
                            paper_bgcolor=_BG, plot_bgcolor=_BG,
                            showlegend=False,
                            xaxis_title="Classe GES", yaxis_title="Annonces",
                        )
                        st.plotly_chart(fig_ges, use_container_width=True)

                with col_ges2:
                    df_dg = df.dropna(subset=["dpe", "ges"])
                    if len(df_dg) >= 5:
                        cross = df_dg.groupby(["dpe", "ges"]).size().reset_index(name="N")
                        fig_cross = px.scatter(
                            cross, x="dpe", y="ges", size="N",
                            color="N", color_continuous_scale="Blues",
                            category_orders={"dpe": DPE_ORDER, "ges": DPE_ORDER},
                            labels={"dpe": "Classe DPE", "ges": "Classe GES", "N": "Annonces"},
                            template="simple_white",
                            title="Corrélation DPE ↔ GES",
                        )
                        fig_cross.update_layout(
                            height=260, margin=dict(t=40, b=10, l=0, r=0),
                            paper_bgcolor=_BG, coloraxis_showscale=False,
                        )
                        st.plotly_chart(fig_cross, use_container_width=True)
                        st.caption("Un bien bien isolé (DPE A) émet aussi peu de CO₂ (GES A) dans la grande majorité des cas.")

    # ── 6. Stats par quartier ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 📍 Statistiques par quartier")
        col_qrt = "nom_commune" if "nom_commune" in df.columns else None
        df_valid = df.dropna(subset=["prix_m2", col_qrt]) if col_qrt else pd.DataFrame()

        if col_qrt and not df_valid.empty:
            rows = []
            for quartier, grp in df_valid.groupby(col_qrt):
                pm2 = [float(v) for v in grp["prix_m2"].tolist() if v == v]
                if len(pm2) < 2:
                    continue
                rows.append({
                    "Quartier":        quartier,
                    "N":               len(pm2),
                    "Moyenne €/m²":    round(_mean(pm2)),
                    "Médiane €/m²":    round(_median(pm2)),
                    "Écart-type €/m²": round(_std(pm2)),
                })

            if rows:
                df_stats = pd.DataFrame(rows).sort_values("Médiane €/m²", ascending=False)
                st.dataframe(
                    df_stats,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Moyenne €/m²":    st.column_config.NumberColumn(format="%d €/m²"),
                        "Médiane €/m²":    st.column_config.NumberColumn(format="%d €/m²"),
                        "Écart-type €/m²": st.column_config.NumberColumn(format="%d €/m²"),
                    },
                )
            else:
                st.info("Pas assez de données par quartier (minimum 2 annonces).")
        else:
            st.info("Colonne quartier absente ou données insuffisantes.")

    # ── 7. Tendances + Projection 2026 ────────────────────────────────────────
    if df_dvf is not None and not df_dvf.empty:
        with st.container(border=True):
            st.markdown("#### 📈 Tendances du marché & projection — Prix/m² médian mensuel")

            _trend = df_dvf[
                df_dvf["type_local"].isin(["Appartement", "Maison"])
                & (df_dvf["surface_reelle_bati"].fillna(0) > 9)
                & (df_dvf["prix_m2"].notna())
                & (df_dvf["prix_m2"] > 500)
            ].copy()

            if not _trend.empty and "date_mutation" in _trend.columns:
                _trend["mois"] = _trend["date_mutation"].dt.to_period("M").astype(str)
                _agg = (
                    _trend.groupby(["mois", "type_local"])["prix_m2"]
                    .median()
                    .reset_index()
                    .rename(columns={"prix_m2": "Prix/m² médian", "type_local": "Type"})
                    .sort_values("mois")
                )

                try:
                    import sys as _sys
                    _root = str(__import__("pathlib").Path(__file__).parent.parent.parent)
                    if _root not in _sys.path:
                        _sys.path.insert(0, _root)
                    from analysis.trend_projection import project_prices

                    fig_trend = go.Figure()
                    COLS_T = {"Appartement": "#E8714A", "Maison": "#1B2B4B"}

                    for ttype in ["Appartement", "Maison"]:
                        sub = _agg[_agg["Type"] == ttype].sort_values("mois")
                        if len(sub) < 3:
                            continue
                        c = COLS_T[ttype]
                        monthly = dict(zip(sub["mois"], sub["Prix/m² médian"]))
                        result  = project_prices(monthly, n_months_ahead=6)

                        h_periods = sorted(result["historique"].keys())
                        h_values  = [result["historique"][p] for p in h_periods]
                        fig_trend.add_trace(go.Scatter(
                            x=h_periods, y=h_values, mode="lines+markers",
                            name=ttype, line=dict(color=c, width=2),
                            marker=dict(size=5),
                        ))

                        p_periods = sorted(result["projection"].keys())
                        p_values  = [result["projection"][p] for p in p_periods]
                        fig_trend.add_trace(go.Scatter(
                            x=[h_periods[-1]] + p_periods,
                            y=[h_values[-1]]  + p_values,
                            mode="lines+markers", name=f"{ttype} (projection)",
                            line=dict(color=c, width=2, dash="dot"),
                            marker=dict(size=4, symbol="diamond"),
                            hovertemplate="%{x} : %{y:,.0f} €/m²<extra>Projection " + ttype + "</extra>",
                        ))

                        beta = result["beta"]
                        var  = result["variation_annuelle_pct"]
                        lbl  = f"{ttype} : {'+' if beta >= 0 else ''}{var:.1f} %/an"
                        if p_periods:
                            fig_trend.add_annotation(
                                x=p_periods[-1], y=p_values[-1],
                                text=lbl, showarrow=False,
                                font=dict(size=11, color=c),
                                xanchor="left", yanchor="middle",
                            )

                    last_hist = sorted(_agg["mois"].unique())[-1]
                    fig_trend.add_vline(
                        x=last_hist, line_dash="dash", line_color="#94A3B8",
                        annotation_text="Aujourd'hui", annotation_position="top left",
                    )
                    fig_trend.update_layout(
                        height=340, margin=dict(t=30, b=10, l=0, r=120),
                        paper_bgcolor=_BG, plot_bgcolor=_BG,
                        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
                        legend_title_text="",
                        xaxis=dict(tickangle=-45),
                    )
                    fig_trend.update_yaxes(tickformat=",.0f", ticksuffix=" €/m²")
                    st.plotly_chart(fig_trend, use_container_width=True)

                except Exception as e:
                    fig_trend = px.line(
                        _agg, x="mois", y="Prix/m² médian", color="Type",
                        color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                        markers=True, template="simple_white",
                    )
                    fig_trend.update_layout(height=300, paper_bgcolor=_BG, plot_bgcolor=_BG)
                    fig_trend.update_yaxes(tickformat=",.0f", ticksuffix=" €/m²")
                    st.plotly_chart(fig_trend, use_container_width=True)
                    st.caption(f"Projection non disponible : {e}")
            else:
                st.info("Données DVF insuffisantes pour calculer les tendances.")

    # ── 8. DVF vs Annonces actuelles ─────────────────────────────────────────
    if df_dvf is not None and not df_dvf.empty and not df.empty:
        with st.container(border=True):
            st.markdown("#### ⚖️ DVF (ventes réelles 2024-2025) vs Annonces actuelles")
            st.caption(
                "Compare le prix/m² des **transactions effectivement réalisées** (DVF, source DGFiP) "
                "au prix/m² **demandé** dans les annonces actuelles. "
                "Un écart positif indique que les vendeurs demandent plus que le marché ne paye réellement."
            )

            rows_cmp = []
            for ttype in ["Appartement", "Maison"]:
                dvf_sub = df_dvf[
                    (df_dvf["type_local"] == ttype)
                    & (df_dvf["prix_m2"].notna())
                    & (df_dvf["prix_m2"] > 500)
                    & (df_dvf["surface_reelle_bati"].fillna(0) > 9)
                ]["prix_m2"]
                if len(dvf_sub) < 5:
                    continue
                dvf_median = float(dvf_sub.median())

                ann_sub = df[(df["type_local"] == ttype) & df["prix_m2"].notna()]["prix_m2"]
                if len(ann_sub) < 2:
                    continue
                ann_median = float(ann_sub.median())

                ecart_pct = round((ann_median - dvf_median) / dvf_median * 100, 1)
                rows_cmp.append({
                    "Type":                 ttype,
                    "DVF €/m² médian":      round(dvf_median),
                    "Annonces €/m² médian": round(ann_median),
                    "Écart (%)":            ecart_pct,
                    "N DVF":                len(dvf_sub),
                    "N annonces":           len(ann_sub),
                })

            if rows_cmp:
                col_c1, col_c2 = st.columns([1, 2], gap="large")
                with col_c1:
                    for r in rows_cmp:
                        st.metric(
                            label=f"Écart annonces vs DVF — {r['Type']}",
                            value=f"{r['Annonces €/m² médian']:,} €/m²",
                            delta=f"{r['Écart (%)']:+.1f} % vs marché réel ({r['DVF €/m² médian']:,} €/m²)",
                        )
                with col_c2:
                    fig_cmp = go.Figure()
                    types = [r["Type"] for r in rows_cmp]
                    dvf_v = [r["DVF €/m² médian"] for r in rows_cmp]
                    ann_v = [r["Annonces €/m² médian"] for r in rows_cmp]
                    fig_cmp.add_trace(go.Bar(
                        name="DVF — ventes réelles", x=types, y=dvf_v,
                        marker_color="#1B2B4B", text=[f"{v:,} €/m²" for v in dvf_v],
                        textposition="outside",
                    ))
                    fig_cmp.add_trace(go.Bar(
                        name="Annonces actuelles", x=types, y=ann_v,
                        marker_color="#E8714A", text=[f"{v:,} €/m²" for v in ann_v],
                        textposition="outside",
                    ))
                    fig_cmp.update_layout(
                        barmode="group", height=280,
                        margin=dict(t=20, b=10, l=0, r=0),
                        paper_bgcolor=_BG, plot_bgcolor=_BG,
                        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
                        template="simple_white",
                    )
                    fig_cmp.update_yaxes(tickformat=",.0f", ticksuffix=" €/m²")
                    st.plotly_chart(fig_cmp, use_container_width=True)
            else:
                st.info("Pas assez de données pour la comparaison DVF / annonces.")
