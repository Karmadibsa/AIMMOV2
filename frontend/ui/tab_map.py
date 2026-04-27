"""Onglet Carte — Visualisation géographique des annonces (Folium)."""

import pandas as pd
import streamlit as st

try:
    import folium
    from streamlit_folium import st_folium
    _FOLIUM_OK = True
except ImportError:
    _FOLIUM_OK = False


# ── Couleurs selon l'écart au marché ─────────────────────────────────────────
def _marker_color(ecart_pct) -> str:
    """Retourne la couleur Folium selon le score d'opportunité."""
    if pd.isna(ecart_pct):
        return "gray"
    ep = float(ecart_pct)
    if ep < -10:
        return "green"
    elif ep < -5:
        return "lightgreen"
    elif ep <= 5:
        return "blue"
    elif ep <= 15:
        return "orange"
    else:
        return "red"


def _popup_html(row: pd.Series) -> str:
    """Génère le HTML du popup Folium pour une annonce."""
    titre   = str(row.get("titre", "Annonce"))[:60]
    prix    = row.get("valeur_fonciere")
    surface = row.get("surface_reelle_bati")
    pm2     = row.get("prix_m2")
    ep      = row.get("ecart_pct") or row.get("dvf_ecart_pct")
    url     = row.get("url", "")
    ttype   = row.get("type_local", "")
    commune = row.get("nom_commune", "")

    prix_str    = f"{prix:,.0f} €"    if pd.notna(prix)    else "—"
    surface_str = f"{surface:.0f} m²" if pd.notna(surface) else "—"
    pm2_str     = f"{pm2:,.0f} €/m²"  if pd.notna(pm2)     else "—"

    badge = ""
    if pd.notna(ep):
        ep_f = float(ep)
        if ep_f < -10:
            badge = f'<span style="background:#DCFCE7;color:#15803D;padding:2px 6px;border-radius:4px;font-weight:700;">🎯 {ep_f:.1f}%</span>'
        elif ep_f < -5:
            badge = f'<span style="background:#D1FAE5;color:#065F46;padding:2px 6px;border-radius:4px;">✅ {ep_f:.1f}%</span>'
        elif ep_f > 10:
            badge = f'<span style="background:#FEF3C7;color:#B45309;padding:2px 6px;border-radius:4px;">⚠️ +{ep_f:.1f}%</span>'

    link = f'<a href="{url}" target="_blank">🔗 Voir l\'annonce</a>' if url else ""

    return f"""
    <div style="font-family:sans-serif;min-width:200px;max-width:280px;">
      <b style="font-size:13px;">{titre}</b><br>
      <small style="color:#64748B;">{ttype} · {commune}</small><br>
      <hr style="margin:4px 0;">
      <b style="font-size:15px;color:#1B2B4B;">{prix_str}</b>
      &nbsp;<span style="color:#64748B;font-size:12px;">{surface_str} · {pm2_str}</span><br>
      {badge}<br>
      <small>{link}</small>
    </div>"""


def render_map(df: pd.DataFrame) -> None:
    """Affiche la carte interactive Folium des annonces."""

    if not _FOLIUM_OK:
        st.warning(
            "⚠️ Les librairies `folium` et `streamlit-folium` ne sont pas installées. "
            "Ajoutez-les à `app/requirements.txt` et redéployez."
        )
        return

    # Annonces avec coordonnées GPS
    df_geo = df.dropna(subset=["latitude", "longitude"]).copy()
    df_geo = df_geo[
        (df_geo["latitude"].between(42.5, 49.0))   # France métropolitaine grosso modo
        & (df_geo["longitude"].between(-5.0, 9.5))
    ]

    if df_geo.empty:
        st.info("😕 Aucune annonce avec coordonnées GPS disponibles.")
        return

    n_geo  = len(df_geo)
    n_tot  = len(df)
    st.caption(f"📍 **{n_geo:,}** annonces géolocalisées sur **{n_tot:,}** au total")

    # ── Légende ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px;font-size:13px;">
      <span>🟢 <b>Opportunité</b> (&lt;−10%)</span>
      <span style="color:#4ade80">🟩 <b>Bonne affaire</b> (−5 à −10%)</span>
      <span style="color:#3b82f6">🔵 <b>Prix marché</b> (−5% à +5%)</span>
      <span style="color:#f97316">🟠 <b>Légèrement élevé</b> (+5 à +15%)</span>
      <span style="color:#ef4444">🔴 <b>Prix élevé</b> (&gt;+15%)</span>
      <span style="color:#94a3b8">⚫ <b>Non évalué</b></span>
    </div>
    """, unsafe_allow_html=True)

    # ── Construction carte ────────────────────────────────────────────────────
    center_lat = float(df_geo["latitude"].median())
    center_lon = float(df_geo["longitude"].median())
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="CartoDB positron",
    )

    # Cluster si beaucoup de points
    try:
        from folium.plugins import MarkerCluster
        cluster = MarkerCluster(
            options={"maxClusterRadius": 50, "disableClusteringAtZoom": 15}
        ).add_to(m)
        target = cluster
    except Exception:
        target = m

    # Ajout des marqueurs
    ecart_col = None
    for col in ["ecart_pct", "dvf_ecart_pct", "qrt_ecart_pct"]:
        if col in df_geo.columns:
            ecart_col = col
            break

    for _, row in df_geo.iterrows():
        ep    = row.get(ecart_col) if ecart_col else None
        color = _marker_color(ep)
        folium.CircleMarker(
            location=[float(row["latitude"]), float(row["longitude"])],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(_popup_html(row), max_width=300),
            tooltip=f"{str(row.get('titre',''))[:40]} — {row.get('valeur_fonciere', 0):,.0f} €",
        ).add_to(target)

    st_folium(m, use_container_width=True, height=520, returned_objects=[])
