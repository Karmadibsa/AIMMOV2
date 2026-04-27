"""
Extraction du DPE (Diagnostic de Performance Énergétique) depuis les textes
d'annonces immobilières.

From scratch — pur Python, pas de regex avancé ni de bibliothèques ML.
Reference : logique métier NidDouillet.

Approche : recherche de patterns textuels fréquents dans les descriptions
scraées (mentions explicites de la lettre DPE ou de formules courantes).
"""

# ── Lettres DPE valides ───────────────────────────────────────────────────────
DPE_LABELS: list[str] = ["A", "B", "C", "D", "E", "F", "G"]

# ── Patterns textuels à rechercher (ordre de priorité : plus précis d'abord) ──
# Chaque tuple : (fragment à chercher dans le texte lower, lettre DPE associée)
# On arrête à la première correspondance.
_PATTERNS: list[tuple[str, str]] = [
    # Formules explicites "DPE X" ou "classe X" ou "étiquette X"
    ("dpe : a",     "A"), ("dpe: a",  "A"), ("dpe a",  "A"), ("classe a",  "A"),
    ("dpe : b",     "B"), ("dpe: b",  "B"), ("dpe b",  "B"), ("classe b",  "B"),
    ("dpe : c",     "C"), ("dpe: c",  "C"), ("dpe c",  "C"), ("classe c",  "C"),
    ("dpe : d",     "D"), ("dpe: d",  "D"), ("dpe d",  "D"), ("classe d",  "D"),
    ("dpe : e",     "E"), ("dpe: e",  "E"), ("dpe e",  "E"), ("classe e",  "E"),
    ("dpe : f",     "F"), ("dpe: f",  "F"), ("dpe f",  "F"), ("classe f",  "F"),
    ("dpe : g",     "G"), ("dpe: g",  "G"), ("dpe g",  "G"), ("classe g",  "G"),
    # Formules "étiquette énergie X"
    ("étiquette énergie a", "A"), ("etiquette energie a", "A"),
    ("étiquette énergie b", "B"), ("etiquette energie b", "B"),
    ("étiquette énergie c", "C"), ("etiquette energie c", "C"),
    ("étiquette énergie d", "D"), ("etiquette energie d", "D"),
    ("étiquette énergie e", "E"), ("etiquette energie e", "E"),
    ("étiquette énergie f", "F"), ("etiquette energie f", "F"),
    ("étiquette énergie g", "G"), ("etiquette energie g", "G"),
    # Formules implicites fréquentes dans les annonces PAP/BienIci
    ("très bien isolé",   "B"), ("bien isolé",       "C"),
    ("isolation récente", "C"), ("isolation bonne",  "C"),
    ("passoire thermique","G"), ("passoire",         "F"),
    ("énergie fossile",   "F"),
]

# ── Mots-clés associés à une mauvaise performance (heuristique) ──────────────
_KEYWORDS_BAD: list[str] = [
    "simple vitrage", "simple-vitrage", "chauffage au fioul",
    "chauffage électrique", "déperditions", "non isolé",
]
_KEYWORDS_GOOD: list[str] = [
    "double vitrage", "triple vitrage", "pompe à chaleur", "pac",
    "panneaux solaires", "bbc", "bâtiment basse consommation",
    "rt 2012", "re 2020",
]


def extract_dpe(description: str | None) -> str | None:
    """
    Extrait la lettre DPE (A-G) depuis le texte d'une annonce immobilière.

    Stratégie (from scratch, sans regex) :
      1. Recherche de patterns explicites par correspondance de sous-chaîne.
      2. Heuristique sur mots-clés si aucun pattern explicite trouvé.
      3. Retourne None si indéterminé.

    Args:
        description (str | None): Texte brut de l'annonce (description).

    Returns:
        str | None: Lettre DPE parmi "A"-"G", ou None si non détectée.
    """
    if not description or not isinstance(description, str):
        return None

    text = description.lower().strip()
    if not text:
        return None

    # ── Étape 1 : patterns explicites ────────────────────────────────────────
    for pattern, lettre in _PATTERNS:
        if pattern in text:
            return lettre

    # ── Étape 2 : heuristique mots-clés ──────────────────────────────────────
    score = 0  # positif → bonne perf, négatif → mauvaise perf
    for kw in _KEYWORDS_GOOD:
        if kw in text:
            score += 1
    for kw in _KEYWORDS_BAD:
        if kw in text:
            score -= 1

    if score >= 2:
        return "B"
    if score == 1:
        return "C"
    if score == -1:
        return "E"
    if score <= -2:
        return "F"

    return None


def enrich_dpe_column(descriptions: list[str | None]) -> list[str | None]:
    """
    Applique extract_dpe() à une liste de descriptions.

    From scratch — boucle for simple, pas de pandas apply.

    Args:
        descriptions (list[str | None]): Liste de textes d'annonces.

    Returns:
        list[str | None]: Liste de lettres DPE (None si non détectée).
    """
    return [extract_dpe(d) for d in descriptions]
