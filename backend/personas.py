"""
Personas acheteurs NidBuyer — filtres ChromaDB et contextes sémantiques.

Chaque persona est un dict avec :
    label      : nom lisible (pour l'UI/logs)
    profil     : clé utilisée par score_opportunite() pour les malus travaux
    budget_max : plafond budgétaire en € (None = sans plafond)
    query      : texte sémantique envoyé à ChromaDB pour la similarité
    filters    : clause where ChromaDB (None = pas de filtre metadata)

Syntaxe ChromaDB where :
    Opérateurs : $eq $ne $gt $gte $lt $lte $and $or
    Les valeurs numériques dans les métadonnées sont stockées en float
    (voir rag._build_metadata), d'où les 0.0 / 3.0 ci-dessous.
"""

PERSONAS: dict[str, dict] = {

    # ── Résidence Principale ──────────────────────────────────────────────────
    "RP": {
        "label":      "Résidence Principale",
        "profil":     "rp",
        "budget_max": 380_000,
        "query":      "appartement familial calme, proche écoles et transports en commun",
        # Budget ≤ 380 k€ ET au moins 3 pièces (T3/T4)
        "filters": {
            "$and": [
                {"prix":      {"$gt":  0.0}},
                {"prix":      {"$lte": 380_000.0}},
                {"nb_pieces": {"$gte": 3.0}},
            ]
        },
    },

    # ── Investisseur locatif ──────────────────────────────────────────────────
    "INV": {
        "label":      "Investisseur Locatif",
        "profil":     "investissement",
        "budget_max": 250_000,
        "query":      "studio ou T2 bien situé, rendement locatif, centre-ville ou proche gare",
        # Budget ≤ 250 k€ — pas de contrainte sur nb_pieces (studio à T2 ok)
        "filters": {
            "$and": [
                {"prix": {"$gt":  0.0}},
                {"prix": {"$lte": 250_000.0}},
            ]
        },
    },

    # ── Résidence Secondaire ──────────────────────────────────────────────────
    "RS": {
        "label":      "Résidence Secondaire",
        "profil":     "rs",
        "budget_max": 200_000,
        "query":      "vue mer ou proche plage, calme, résidence secondaire Toulon",
        # Budget ≤ 200 k€
        "filters": {
            "$and": [
                {"prix": {"$gt":  0.0}},
                {"prix": {"$lte": 200_000.0}},
            ]
        },
    },

    # ── Immeuble Mixte ────────────────────────────────────────────────────────
    "MIX": {
        "label":      "Immeuble Mixte",
        "profil":     "mixte",
        "budget_max": None,
        "query":      "immeuble de rapport, local commercial et logements, investissement mixte",
        # Type de bien = "Immeuble" (valeur telle qu'indexée depuis Supabase)
        "filters": {
            "type_bien": {"$eq": "Immeuble"}
        },
    },
}

# Valeurs valides pour la validation dans les routes FastAPI
PERSONA_IDS: list[str] = list(PERSONAS.keys())
