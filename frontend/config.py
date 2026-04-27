"""
Constantes globales de l'application NidDouillet by AImmo.
Toutes les valeurs statiques (URLs, chemins, dictionnaires) sont ici.
"""

from pathlib import Path

# ── URLs & Chemins ──────────────────────────────────────────────────────────────
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/Karmadibsa/AImmo/"
    "feat/axel-verification/data/annonces.csv"
)
CSV_PATH     = Path(__file__).parent.parent / "data" / "annonces.csv"
DVF_CSV_PATH = Path(__file__).parent.parent / "data" / "dvf_toulon.csv"

# ── Filtres prix/m² pour la régression DVF (supprime les outliers) ──────────────
# Appartements : 3 500 – 10 000 €/m²   Maisons : 2 000 – 6 000 €/m²
DVF_PM2_FILTERS: dict[str, tuple[int, int]] = {
    "Appartement": (3_500, 10_000),
    "Maison":      (2_000,  6_000),
}

# ── Tags NLP (extraction depuis description) ────────────────────────────────────
NLP_TAGS: dict[str, tuple[list[str], str]] = {
    "Vue mer":    (["vue mer", "vue sur la mer", "vue panoramique"],    "tag-sea"),
    "Terrasse":   (["terrasse"],                                        "tag-green"),
    "Balcon":     (["balcon"],                                          "tag-green"),
    "Parking":    (["parking", "stationnement", "place de parking"],    "tag-orange"),
    "Garage":     (["garage", "box"],                                   "tag-orange"),
    "Ascenseur":  (["ascenseur"],                                       "tag-blue"),
    "Rénové":     (["refait", "rénové", "rénovation", "neuf", "neuve"], "tag-green"),
    "Cave":       (["cave"],                                            "tag-orange"),
    "Piscine":    (["piscine"],                                         "tag-blue"),
    "Proche mer": (["bord de mer", "pieds dans l'eau", "plages",
                    "proche mer", "400 mètres"],                        "tag-sea"),
}

# ── Coefficients DVF — valeurs de repli (fallback) ──────────────────────────────
# Utilisés uniquement si dvf_toulon.csv est absent ou illisible.
# Pour les valeurs dynamiques (R²≈0.67), voir data_loader.get_dvf_models().
DVF_REGRESSION: dict[str, dict] = {
    "Appartement": {"slope": 4_415.5, "intercept":  21_628.1, "r2": 0.671, "n": 1_040},
    "Maison":      {"slope": 3_436.4, "intercept":  70_802.9, "r2": 0.477, "n":   366},
}
