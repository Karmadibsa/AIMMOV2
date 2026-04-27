-- =============================================================================
-- DDL : table "annonces"
-- À exécuter dans : Supabase Console → SQL Editor → New Query
-- Objectif : stocker les annonces immobilières scrappées (migration V1 + inserts futurs)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.annonces (
    -- Clé primaire auto-générée côté Supabase
    id                       BIGSERIAL PRIMARY KEY,

    -- Source du scraping (ex : "pap", "leboncoin", "seloger")
    source                   TEXT,

    -- Type de bien ("Appartement", "Maison", …)
    type_local               TEXT,

    -- Titre brut de l'annonce
    titre                    TEXT,

    -- Prix affiché en euros (peut être NULL si non renseigné)
    valeur_fonciere          NUMERIC(12, 2),

    -- Surface habitable en m²
    surface_reelle_bati      NUMERIC(8, 2),

    -- Nombre de pièces principales
    nombre_pieces_principales NUMERIC(4, 1),

    -- Localisation
    nom_commune              TEXT,
    code_postal              TEXT,
    code_departement         TEXT,

    -- Coordonnées GPS (NULL si non geocodé)
    longitude                NUMERIC(11, 7),
    latitude                 NUMERIC(11, 7),

    -- Texte complet de l'annonce
    description              TEXT,

    -- URL canonique de l'annonce (doit être unique pour éviter les doublons)
    url                      TEXT UNIQUE,

    -- Date de première scraping / mutation DVF
    date_mutation            TIMESTAMPTZ,

    -- Horodatage d'insertion en base (automatique)
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Index utiles pour les requêtes métier ──────────────────────────────────────

-- Filtres fréquents : commune, type, prix
CREATE INDEX IF NOT EXISTS idx_annonces_commune      ON public.annonces (nom_commune);
CREATE INDEX IF NOT EXISTS idx_annonces_type_local   ON public.annonces (type_local);
CREATE INDEX IF NOT EXISTS idx_annonces_prix         ON public.annonces (valeur_fonciere);
CREATE INDEX IF NOT EXISTS idx_annonces_surface      ON public.annonces (surface_reelle_bati);

-- Tri par date de scraping (flux "nouvelles annonces")
CREATE INDEX IF NOT EXISTS idx_annonces_created_at   ON public.annonces (created_at DESC);

-- ── Row Level Security (optionnel mais recommandé en prod) ────────────────────
-- Désactivé pour le dev ; activer avant mise en prod.
-- ALTER TABLE public.annonces ENABLE ROW LEVEL SECURITY;
