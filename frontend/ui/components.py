"""
Composants HTML réutilisables et helpers NLP.
"""

import streamlit as st

from config import NLP_TAGS

# Mapping colonne Supabase (booléenne) → (label affiché, classe CSS)
# Priorité sur l'extraction textuelle : donnée directe de l'API BienIci.
_BOOL_TAGS: list[tuple[str, str, str]] = [
    ("terrasse",       "Terrasse",       "tag-green"),
    ("balcon",         "Balcon",         "tag-green"),
    ("jardin",         "Jardin",         "tag-green"),
    ("parking",        "Parking",        "tag-orange"),
    ("cave",           "Cave",           "tag-orange"),
    ("piscine",        "Piscine",        "tag-blue"),
    ("ascenseur",      "Ascenseur",      "tag-blue"),
    ("cheminee",       "Cheminée",       "tag-orange"),
    ("climatisation",  "Climatisation",  "tag-blue"),
    ("vue_degagee",    "Vue dégagée",    "tag-sea"),
]

# Tags détectables uniquement par texte (aucune colonne booléenne disponible)
_TEXT_ONLY_TAGS: list[tuple[str, list[str], str]] = [
    ("Vue mer",    ["vue mer", "vue sur la mer"],                     "tag-sea"),
    ("Proche mer", ["bord de mer", "pieds dans l'eau", "proche mer"], "tag-sea"),
    ("Rénové",     ["refait", "rénové", "rénovation"],                "tag-green"),
    ("Garage",     ["garage", "box"],                                 "tag-orange"),
    ("Neuf",       ["neuf", "neuve", "programme neuf"],               "tag-green"),
]


def build_tags_from_row(row) -> list[tuple[str, str]]:
    """
    Construit les tags d'une annonce en prioritisant les colonnes booléennes
    Supabase (fiables, source API BienIci), puis complète avec l'extraction
    textuelle pour les attributs sans colonne dédiée.

    Args:
        row: dict ou pd.Series représentant une ligne d'annonce.

    Returns:
        Liste de (label, classe_css) pour l'affichage.
    """
    tags: list[tuple[str, str]] = []
    seen: set[str] = set()

    # 1. Colonnes booléennes directes (priorité absolue)
    for col, lbl, css in _BOOL_TAGS:
        val = row.get(col) if hasattr(row, "get") else getattr(row, col, None)
        if val is True or val == 1 or str(val).lower() == "true":
            tags.append((lbl, css))
            seen.add(lbl)

    # 2. Texte uniquement pour ce qui n'a pas de colonne booléenne
    desc = row.get("description") if hasattr(row, "get") else getattr(row, "description", "")
    if isinstance(desc, str):
        d = desc.lower()
        for lbl, kws, css in _TEXT_ONLY_TAGS:
            if lbl not in seen and any(k in d for k in kws):
                tags.append((lbl, css))

    return tags


def extract_tags(description: str) -> list[tuple[str, str]]:
    """
    Extraction textuelle legacy (NLP_TAGS depuis config).
    Préférer build_tags_from_row() quand la ligne complète est disponible.
    """
    if not isinstance(description, str):
        return []
    d = description.lower()
    return [(lbl, css) for lbl, (kws, css) in NLP_TAGS.items() if any(k in d for k in kws)]


@st.fragment
def photo_carousel(photos_raw, key: str) -> None:
    """
    Affiche un carousel de photos avec navigation ◀ / ▶.
    @st.fragment isole le rerun au carousel uniquement — pas de freeze global.

    Args:
        photos_raw : str (JSON) ou list d'URLs.
        key        : identifiant unique pour éviter les conflits de widget.
    """
    import json as _json

    # Parse le JSON si nécessaire
    if isinstance(photos_raw, str):
        try:
            photos = _json.loads(photos_raw)
        except Exception:
            return
    elif isinstance(photos_raw, list):
        photos = photos_raw
    else:
        return

    photos = [p for p in photos if isinstance(p, str) and p.startswith("http")]
    if not photos:
        return

    n = len(photos)

    if n == 1:
        st.image(photos[0], use_container_width=True)
        return

    # Index courant stocké en session_state
    state_key = f"carousel_idx_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    idx = max(0, min(st.session_state[state_key], n - 1))

    st.image(photos[idx], use_container_width=True)

    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("◀", key=f"car_prev_{key}", disabled=(idx == 0),
                     use_container_width=True):
            st.session_state[state_key] = idx - 1
            st.rerun()
    with col_info:
        st.caption(f"📷 {idx + 1} / {n}")
    with col_next:
        if st.button("▶", key=f"car_next_{key}", disabled=(idx >= n - 1),
                     use_container_width=True):
            st.session_state[state_key] = idx + 1
            st.rerun()


def tags_html(tags: list[tuple[str, str]]) -> str:
    """Génère le HTML pour afficher les tags NLP."""
    return "".join(f'<span class="tag {css}">{lbl}</span>' for lbl, css in tags)


def market_badge_html(ecart_pct: float) -> str:
    """Badge HTML coloré selon la classification marché (4 niveaux)."""
    if ecart_pct < -10:
        return f'<span class="badge-opport">🎯 OPPORTUNITÉ &nbsp;{ecart_pct:.0f}%</span>'
    elif ecart_pct < -5:
        return f'<span class="badge-bonne">✅ Bonne affaire &nbsp;{ecart_pct:.0f}%</span>'
    elif ecart_pct <= 5:
        return f'<span class="badge-normal">✅ Prix normal &nbsp;{ecart_pct:+.0f}%</span>'
    else:
        return f'<span class="badge-eleve">⚠️ Prix élevé &nbsp;{ecart_pct:+.0f}%</span>'
