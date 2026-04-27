"""
Script de migration one-shot : AImmoV1/data/annonces.csv → Supabase (table "annonces")

Usage :
    1. Créer la table via create_table_annonces.sql dans la console Supabase.
    2. Renseigner SUPABASE_URL et SUPABASE_KEY dans AIMMOV2/.env
    3. Lancer depuis la racine de AIMMOV2/ :
           python migrate_v1_to_supabase.py

Dépendances :
    - supabase-py  (ajouté au requirements.txt)
    - python-dotenv (déjà présent)

Contraintes techniques :
    - Lecture du CSV avec le module standard `csv` (pas de pandas).
    - Inserts par lots de BATCH_SIZE pour ne pas saturer l'API Supabase.
    - Gestion des doublons via la contrainte UNIQUE sur la colonne `url`
      (upsert avec on_conflict="url" → skip silencieux).
"""

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# ── Configuration ──────────────────────────────────────────────────────────────

# Le .env se trouve à la racine de AIMMOV2/
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]

# Chemin vers le CSV V1 (relatif à ce script, donc racine AIMMOV2/)
CSV_PATH = Path(__file__).parent.parent / "AImmoV1" / "data" / "annonces.csv"

# Taille des lots d'insertion (évite les timeouts sur de grands jeux de données)
BATCH_SIZE = 50


# ── Helpers de conversion ──────────────────────────────────────────────────────

def _to_float_or_none(value: str) -> float | None:
    """Convertit une chaîne en float ; retourne None si vide ou invalide."""
    if value is None or value.strip() == "":
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def _to_str_or_none(value: str) -> str | None:
    """Retourne None si la chaîne est vide, sinon la chaîne nettoyée."""
    if value is None or value.strip() == "":
        return None
    return value.strip()


def parse_row(row: dict) -> dict:
    """
    Transforme une ligne brute du CSV (dict str→str) en dict prêt pour Supabase.

    Mapping CSV → colonnes SQL :
        source                   → source
        type_local               → type_local
        titre                    → titre
        valeur_fonciere          → valeur_fonciere  (NUMERIC)
        surface_reelle_bati      → surface_reelle_bati (NUMERIC)
        nombre_pieces_principales → nombre_pieces_principales (NUMERIC)
        nom_commune              → nom_commune
        code_postal              → code_postal
        code_departement         → code_departement
        longitude                → longitude (NUMERIC)
        latitude                 → latitude  (NUMERIC)
        description              → description
        url                      → url
        date_mutation            → date_mutation (TIMESTAMPTZ)
    """
    return {
        "source":                    _to_str_or_none(row.get("source", "")),
        "type_local":                _to_str_or_none(row.get("type_local", "")),
        "titre":                     _to_str_or_none(row.get("titre", "")),
        "valeur_fonciere":           _to_float_or_none(row.get("valeur_fonciere", "")),
        "surface_reelle_bati":       _to_float_or_none(row.get("surface_reelle_bati", "")),
        "nombre_pieces_principales": _to_float_or_none(row.get("nombre_pieces_principales", "")),
        "nom_commune":               _to_str_or_none(row.get("nom_commune", "")),
        "code_postal":               _to_str_or_none(row.get("code_postal", "")),
        "code_departement":          _to_str_or_none(row.get("code_departement", "")),
        "longitude":                 _to_float_or_none(row.get("longitude", "")),
        "latitude":                  _to_float_or_none(row.get("latitude", "")),
        "description":               _to_str_or_none(row.get("description", "")),
        "url":                       _to_str_or_none(row.get("url", "")),
        # On normalise la date : Supabase accepte les ISO 8601
        "date_mutation":             _to_str_or_none(row.get("date_mutation", "")),
    }


# ── Lecture du CSV ─────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    """
    Lit le CSV V1 avec le module standard `csv`.
    Retourne une liste de dicts déjà nettoyés/typés pour Supabase.
    Ignore silencieusement les lignes sans URL (impossible d'éviter les doublons).
    """
    if not path.exists():
        print(f"[ERREUR] Fichier introuvable : {path}", file=sys.stderr)
        sys.exit(1)

    records = []
    skipped = 0

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            parsed = parse_row(raw_row)
            if parsed["url"] is None:
                # Sans URL on ne peut pas déduplication → on skip
                skipped += 1
                continue
            records.append(parsed)

    print(f"[CSV] {len(records)} lignes valides chargées ({skipped} ignorées sans URL).")
    return records


# ── Insertion par lots dans Supabase ──────────────────────────────────────────

def migrate(client: Client, records: list[dict]) -> None:
    """
    Insère les annonces dans Supabase par lots de BATCH_SIZE.
    Utilise upsert + ignore_duplicates=True pour sauter les doublons
    (contrainte UNIQUE sur `url`).
    """
    total = len(records)
    inserted = 0
    skipped = 0

    for start in range(0, total, BATCH_SIZE):
        batch = records[start : start + BATCH_SIZE]
        try:
            # upsert : ignore_duplicates évite l'erreur sur url déjà existante
            response = (
                client.table("annonces")
                .upsert(batch, on_conflict="url", ignore_duplicates=True)
                .execute()
            )
            # supabase-py v2 lève une exception en cas d'erreur HTTP
            # → on peut compter les données retournées comme indicateur
            batch_inserted = len(response.data) if response.data else 0
            batch_skipped = len(batch) - batch_inserted
            inserted += batch_inserted
            skipped += batch_skipped
            print(
                f"  Lot {start + 1}–{min(start + BATCH_SIZE, total)} : "
                f"{batch_inserted} insérées, {batch_skipped} ignorées (doublons)."
            )
        except Exception as exc:
            print(f"[ERREUR] Lot {start}–{start + BATCH_SIZE} : {exc}", file=sys.stderr)
            # On continue sur le prochain lot plutôt que de tout arrêter
            continue

    print(f"\n[RÉSULTAT] {inserted} annonces insérées, {skipped} doublons ignorés sur {total} traitées.")


# ── Point d'entrée ─────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Migration V1 → Supabase : NidBuyer")
    print("=" * 60)
    print(f"Lecture de : {CSV_PATH}")
    print(f"Destination : {SUPABASE_URL}\n")

    # 1. Charger le CSV
    records = load_csv(CSV_PATH)

    # 2. Créer le client Supabase
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 3. Insérer dans Supabase
    print(f"\nInsertion en lots de {BATCH_SIZE}…")
    migrate(client, records)

    print("\nMigration terminée.")


if __name__ == "__main__":
    main()
