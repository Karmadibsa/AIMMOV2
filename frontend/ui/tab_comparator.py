"""Onglet Comparateur — comparaison côte à côte de 2 à 4 biens."""

import pandas as pd
import streamlit as st

from ui.components import photo_carousel, tags_html

MAX_COMPARE = 4

# Ordre et libellés des métriques comparées
_METRICS: list[tuple[str, str, str]] = [
    # (colonne,                  label,            sens)
    # sens = "low"  → valeur la plus basse = meilleure (prix)
    # sens = "high" → valeur la plus haute = meilleure (surface, DPE score)
    # sens = ""     → pas de colorisation
    ("valeur_fonciere",           "💰 Prix",                "low"),
    ("prix_m2",                   "📐 Prix/m²",             "low"),
    ("surface_reelle_bati",       "📏 Surface",             "high"),
    ("nombre_pieces_principales", "🚪 Pièces",              "high"),
    ("dpe",                       "🌿 DPE",                 "low_letter"),
    ("ges",                       "💨 GES",                 "low_letter"),
    ("energie_valeur",            "⚡ Énergie kWhEP/m²/an", "low"),
    ("nom_commune",               "📍 Commune",             ""),
    ("annee_construction",        "🏗️ Construction",        ""),
    ("ecart_pct",                 "📊 Écart marché (%)",    "low"),
    ("dvf_ecart_pct",             "🏦 Écart DVF (%)",       "low"),
    ("prix_baisse",               "📉 Prix en baisse",      ""),
]

_DPE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6}


def _fmt(col: str, val) -> str:
    """Formate une valeur pour l'affichage dans le tableau comparatif."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    if col == "valeur_fonciere":
        return f"{val:,.0f} €"
    if col == "prix_m2":
        return f"{val:,.0f} €/m²"
    if col == "surface_reelle_bati":
        return f"{val:.0f} m²"
    if col == "nombre_pieces_principales":
        return str(int(val))
    if col == "energie_valeur":
        return f"{int(val)} kWhEP/m²/an"
    if col == "ecart_pct":
        return f"{float(val):+.1f}%"
    if col == "dvf_ecart_pct":
        return f"{float(val):+.1f}%"
    if col == "prix_baisse":
        return "✅ Oui" if (val is True or val == 1) else "Non"
    if col == "annee_construction":
        try:
            return str(int(val))
        except Exception:
            return str(val)
    return str(val)


def _best_indices(col: str, sens: str, rows: list[dict]) -> set[int]:
    """Retourne les indices des biens ayant la meilleure valeur pour cette métrique."""
    if not sens:
        return set()

    vals = []
    for i, r in enumerate(rows):
        v = r.get(col)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            vals.append(None)
        else:
            vals.append(v)

    valid = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(valid) < 2:
        return set()

    if sens == "low":
        best = min(v for _, v in valid)
        return {i for i, v in valid if v == best}
    if sens == "high":
        best = max(v for _, v in valid)
        return {i for i, v in valid if v == best}
    if sens == "low_letter":
        ranks = [(i, _DPE_RANK.get(str(v).upper(), 99)) for i, v in valid]
        best_rank = min(r for _, r in ranks)
        return {i for i, r in ranks if r == best_rank}
    return set()


def _worst_indices(col: str, sens: str, rows: list[dict]) -> set[int]:
    """Retourne les indices des biens ayant la moins bonne valeur."""
    if not sens:
        return set()

    vals = []
    for i, r in enumerate(rows):
        v = r.get(col)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            vals.append(None)
        else:
            vals.append(v)

    valid = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(valid) < 2:
        return set()

    if sens == "low":
        worst = max(v for _, v in valid)
        return {i for i, v in valid if v == worst}
    if sens == "high":
        worst = min(v for _, v in valid)
        return {i for i, v in valid if v == worst}
    if sens == "low_letter":
        ranks = [(i, _DPE_RANK.get(str(v).upper(), 99)) for i, v in valid]
        worst_rank = max(r for _, r in ranks)
        return {i for i, r in ranks if r == worst_rank}
    return set()


def render_comparator(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("😕 Aucune donnée disponible.")
        return

    st.markdown("### ⚖️ Comparateur de biens")
    st.caption("Sélectionnez 2 à 4 biens pour les comparer côte à côte.")

    # ── Zone de sélection ─────────────────────────────────────────────────────
    with st.container(border=True):
        # Recherche texte pour pré-filtrer la liste
        search = st.text_input(
            "🔍 Rechercher un bien",
            placeholder="Tapez un titre, une commune, un quartier…",
            key="cmp_search",
        )

        # Filtrage du dataframe pour le multiselect
        df_sel = df.copy()
        if search:
            mask = (
                df_sel["titre"].fillna("").str.contains(search, case=False) |
                df_sel["nom_commune"].fillna("").str.contains(search, case=False) |
                df_sel["description"].fillna("").str.contains(search, case=False)
            )
            df_sel = df_sel[mask]

        # Construction des labels pour le multiselect
        def _make_label(row) -> str:
            t     = str(row.get("type_local", "Bien"))[:10]
            titre = str(row.get("titre", ""))[:40]
            prix  = row.get("valeur_fonciere")
            surf  = row.get("surface_reelle_bati")
            comm  = str(row.get("nom_commune", ""))
            parts = [t]
            if pd.notna(prix):  parts.append(f"{prix:,.0f} €")
            if pd.notna(surf):  parts.append(f"{surf:.0f} m²")
            if comm:            parts.append(comm)
            return f"{titre}  ·  " + "  ·  ".join(parts)

        labels     = [_make_label(r) for _, r in df_sel.iterrows()]
        url_by_lbl = {lbl: row.get("url", "") for lbl, (_, row) in zip(labels, df_sel.iterrows())}

        # Compteur de reset : changer le key du multiselect force sa réinitialisation
        # (écrire directement dans session_state["cmp_selected"] lève une exception Streamlit)
        if "cmp_reset_count" not in st.session_state:
            st.session_state["cmp_reset_count"] = 0
        reset_n = st.session_state["cmp_reset_count"]

        col_select, col_reset = st.columns([8, 1])
        with col_select:
            selected_labels = st.multiselect(
                f"Sélectionner les biens à comparer (2 à {MAX_COMPARE} maximum)",
                options=labels,
                max_selections=MAX_COMPARE,
                placeholder="Sélectionnez un bien…",
                key=f"cmp_selected_{reset_n}",
            )
        with col_reset:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key="cmp_clear", use_container_width=True,
                         help="Vider la sélection"):
                st.session_state["cmp_reset_count"] += 1
                st.rerun()

        n_sel = len(selected_labels)
        if n_sel == 0:
            st.caption("Sélectionnez au moins 2 biens pour lancer la comparaison.")
        elif n_sel == 1:
            st.caption("Ajoutez encore au moins 1 bien.")
        else:
            st.caption(f"✅ {n_sel} biens sélectionnés — comparaison ci-dessous.")

    if len(selected_labels) < 2:
        return

    # ── Récupération des lignes sélectionnées ─────────────────────────────────
    # On garde l'ordre de sélection
    selected_rows: list[dict] = []
    for lbl in selected_labels:
        target_url = url_by_lbl.get(lbl)
        # cherche dans df_sel d'abord, puis dans df complet
        for frame in (df_sel, df):
            if "url" in frame.columns:
                match = frame[frame["url"] == target_url]
                if not match.empty:
                    selected_rows.append(match.iloc[0].to_dict())
                    break

    if not selected_rows:
        st.warning("Impossible de retrouver les biens sélectionnés.")
        return

    n = len(selected_rows)

    # ── En-têtes (photo + titre + lien) ──────────────────────────────────────
    st.markdown("---")
    header_cols = st.columns(n)
    for i, (col, row) in enumerate(zip(header_cols, selected_rows)):
        with col:
            photos = row.get("photos")
            if photos is not None:
                photo_carousel(photos, key=f"cmp_{i}")
            titre = str(row.get("titre", "Annonce"))
            st.markdown(f"**{titre[:60]}{'…' if len(titre) > 60 else ''}**")
            url = row.get("url")
            if url and pd.notna(url):
                st.markdown(f"[🔗 Voir l'annonce]({url})")

    # ── Tableau comparatif ────────────────────────────────────────────────────
    st.markdown("---")

    for col_name, label, sens in _METRICS:
        # N'affiche la ligne que si au moins un bien a la donnée
        has_data = any(
            r.get(col_name) is not None and
            not (isinstance(r.get(col_name), float) and pd.isna(r.get(col_name)))
            for r in selected_rows
        )
        if not has_data:
            continue

        best_idx  = _best_indices(col_name, sens, selected_rows)
        worst_idx = _worst_indices(col_name, sens, selected_rows)

        row_cols = st.columns([1.2] + [1] * n)

        # Label de la métrique (colonne 0)
        with row_cols[0]:
            st.markdown(
                f'<div style="padding:6px 4px;font-size:13px;'
                f'color:#475569;font-weight:600;">{label}</div>',
                unsafe_allow_html=True,
            )

        # Valeur pour chaque bien
        for i, row in enumerate(selected_rows):
            val      = row.get(col_name)
            val_str  = _fmt(col_name, val)
            has_val  = val is not None and not (isinstance(val, float) and pd.isna(val))

            if not has_val:
                bg = "#f8fafc"
                fg = "#94a3b8"
                fw = "400"
            elif i in best_idx:
                bg = "#dcfce7"   # vert clair
                fg = "#166534"
                fw = "700"
            elif i in worst_idx:
                bg = "#fee2e2"   # rouge clair
                fg = "#991b1b"
                fw = "700"
            else:
                bg = "#f8fafc"
                fg = "#1e293b"
                fw = "500"

            with row_cols[i + 1]:
                st.markdown(
                    f'<div style="background:{bg};color:{fg};font-weight:{fw};'
                    f'padding:6px 10px;border-radius:6px;font-size:13px;'
                    f'text-align:center;margin:2px 0;">{val_str}</div>',
                    unsafe_allow_html=True,
                )

    # ── Tags ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    tag_cols = st.columns([1.2] + [1] * n)
    with tag_cols[0]:
        st.markdown(
            '<div style="padding:6px 4px;font-size:13px;color:#475569;font-weight:600;">'
            '🏷️ Équipements</div>',
            unsafe_allow_html=True,
        )
    for i, row in enumerate(selected_rows):
        tags = row.get("tags", [])
        with tag_cols[i + 1]:
            if tags:
                st.markdown(tags_html(tags), unsafe_allow_html=True)
            else:
                st.caption("—")

    # ── Descriptions ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### 📝 Descriptions")
    desc_cols = st.columns(n)
    for i, (col, row) in enumerate(zip(desc_cols, selected_rows)):
        desc = str(row.get("description", "")).strip()
        with col:
            if desc and desc != "nan":
                st.markdown(
                    f"<small style='color:#475569;line-height:1.6'>"
                    f"{desc[:500]}{'…' if len(desc) > 500 else ''}</small>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Pas de description.")
