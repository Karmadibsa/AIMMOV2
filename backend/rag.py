"""
Indexation vectorielle et recherche sémantique — NidBuyer V2.

Responsabilités :
  1. Maintenir la connexion à la collection ChromaDB locale.
  2. `indexer_depuis_supabase()` : initialisation one-shot (lit toutes les
     annonces depuis Supabase et les charge dans ChromaDB).
  3. `indexer_annonces()` : appelé par ingestion.py pour les nouvelles annonces.
  4. `search_similar()` : requête sémantique en langage naturel.

Colonnes Supabase réelles (schéma actuel) :
    prix, surface, pieces, lien, quartier, date_publication, description,
    dpe, ges, terrasse, balcon, parking, travaux, neuf, ascenseur, type_bien

Lancement de l'indexation initiale (depuis la racine de AIMMOV2/) :
    python -m backend.rag
"""

import hashlib
import logging
import os
from pathlib import Path

# Désactive la télémétrie anonyme de ChromaDB (évite le bruit dans les logs)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# ── ChromaDB ──────────────────────────────────────────────────────────────────

CHROMA_PATH      = str(Path(__file__).parent.parent / "chroma_db")
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
COLLECTION_NAME  = "annonces_toulon"
INDEX_BATCH_SIZE = 100

# Initialisation paresseuse — créés au premier appel, pas à l'import.
# Permet : (1) démarrage rapide d'uvicorn, (2) monkeypatching dans les tests.
_client: chromadb.ClientAPI | None = None
_ef = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        path = os.environ.get("CHROMA_PATH", CHROMA_PATH)
        _client = chromadb.PersistentClient(path=path)
    return _client


def _get_ef():
    global _ef
    if _ef is None:
        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _ef


def get_collection() -> chromadb.Collection:
    """Retourne (ou crée) la collection ChromaDB des annonces."""
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_ef(),
        metadata={"hnsw:space": "cosine"},
    )


# ── Construction du texte à encoder ───────────────────────────────────────────

def _build_document(annonce: dict) -> str:
    """
    Construit le texte brut encodé en vecteur.
    Enrichi avec les caractéristiques qualitatives (DPE, extérieurs)
    pour améliorer la pertinence de la recherche sémantique.
    """
    parts = []

    if annonce.get("type_bien"):
        parts.append(annonce["type_bien"])

    if annonce.get("surface") is not None:
        parts.append(f"{annonce['surface']} m²")

    if annonce.get("pieces") is not None:
        parts.append(f"{annonce['pieces']} pièces")

    if annonce.get("quartier"):
        parts.append(f"à {annonce['quartier']}")

    if annonce.get("prix") is not None:
        parts.append(f"{annonce['prix']} €")

    # Caractéristiques qualitatives → améliorent le matching sémantique
    features = []
    if annonce.get("terrasse"):  features.append("terrasse")
    if annonce.get("balcon"):    features.append("balcon")
    if annonce.get("parking"):   features.append("parking")
    if annonce.get("ascenseur"): features.append("ascenseur")
    if annonce.get("neuf"):      features.append("neuf")
    if annonce.get("travaux"):   features.append("travaux à prévoir")
    if features:
        parts.append(", ".join(features))

    if annonce.get("dpe"):
        parts.append(f"DPE {annonce['dpe']}")

    description = annonce.get("description") or ""
    if description:
        parts.append(description[:800])

    return " — ".join(parts) if parts else "Annonce sans description"


def _build_metadata(annonce: dict) -> dict:
    """
    Construit le dict de métadonnées stocké dans ChromaDB.

    Types acceptés par ChromaDB : str, int, float, bool.
    Les champs None sont convertis en valeurs neutres.
    Les booléens Supabase sont stockés en int (0/1) pour la compatibilité
    des filtres where ($eq, $gte…).
    """
    def _s(val, default: str = "") -> str:
        return default if val is None else str(val)

    def _f(val, default: float = 0.0) -> float:
        try:
            return float(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    def _b(val) -> int:
        """bool Supabase (True/False/None) → int ChromaDB (1/0)."""
        return 1 if val else 0

    return {
        # ── Identification ──────────────────────────────────────────────────
        "id":         _s(annonce.get("id")),
        "lien":       _s(annonce.get("lien")),
        "titre":      _s(annonce.get("titre")),
        "source":     _s(annonce.get("source")),
        # ── Géographie ─────────────────────────────────────────────────────
        "quartier":   _s(annonce.get("quartier")),
        "type_bien": _s(annonce.get("type_bien")),
        # ── Chiffres (utilisés dans les filtres where des Personas) ────────
        "prix":       _f(annonce.get("prix")),
        "surface":    _f(annonce.get("surface")),
        "nb_pieces":  _f(annonce.get("pieces")),
        # ── Qualité énergétique ─────────────────────────────────────────────
        "dpe":        _s(annonce.get("dpe")),
        "ges":        _s(annonce.get("ges")),
        # ── Caractéristiques booléennes (pour futurs filtres Personas) ─────
        "terrasse":   _b(annonce.get("terrasse")),
        "balcon":     _b(annonce.get("balcon")),
        "parking":    _b(annonce.get("parking")),
        "ascenseur":  _b(annonce.get("ascenseur")),
        "travaux":    _b(annonce.get("travaux")),
        "neuf":       _b(annonce.get("neuf")),
        # ── Géolocalisation (pour la carte Streamlit) ───────────────────────
        "latitude":   _f(annonce.get("latitude")),
        "longitude":  _f(annonce.get("longitude")),
    }


def _build_chroma_id(annonce: dict) -> str:
    """
    ID stable pour ChromaDB basé sur le lien (déduplication idempotente).
    Fallback sur l'id Supabase si le lien est absent.
    Pas de préfixe — les tests attendent de retrouver l'id exact (ex: "001").
    """
    lien = annonce.get("lien") or annonce.get("url") or annonce.get("url_source")
    if lien:
        return hashlib.md5(lien.encode()).hexdigest()
    raw_id = annonce.get("id", "unknown")
    return str(raw_id)


# ── Indexation ────────────────────────────────────────────────────────────────

def indexer_annonces(annonces: list[dict]) -> int:
    """
    Indexe une liste d'annonces dans ChromaDB (upsert idempotent).

    Appelé par ingestion.py pour les nouvelles annonces issues des scrapers.

    Returns:
        Nombre de documents envoyés à ChromaDB.
    """
    if not annonces:
        logger.info("indexer_annonces() : liste vide, rien à faire.")
        return 0

    collection = get_collection()
    total = 0

    for start in range(0, len(annonces), INDEX_BATCH_SIZE):
        batch     = annonces[start: start + INDEX_BATCH_SIZE]
        ids       = [_build_chroma_id(a)  for a in batch]
        documents = [_build_document(a)   for a in batch]
        metadatas = [_build_metadata(a)   for a in batch]

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        total += len(batch)
        logger.info(
            "  ChromaDB : lot %d–%d indexé (%d/%d)",
            start + 1, start + len(batch), total, len(annonces),
        )

    return total


# ── Indexation initiale depuis Supabase ───────────────────────────────────────

# Colonnes sélectionnées — schéma réel de la table annonces
_SELECT_COLONNES = (
    "id, source, type_bien, titre, "
    "prix, surface, pieces, quartier, lien, date_publication, "
    "description, "
    "dpe, ges, travaux, neuf, terrasse, balcon, parking, ascenseur, "
    "latitude, longitude"
)


def indexer_depuis_supabase(
    page_size: int = 1000,
    verbose: bool = True,
) -> dict:
    """
    Charge TOUTES les annonces depuis Supabase et les indexe dans ChromaDB.

    Stratégie de pagination : blocs de `page_size` lignes via range() jusqu'à
    obtenir un lot vide (fin de table). Upsert idempotent — relancer est sûr.

    Returns:
        dict : total_supabase, total_indexe, deja_presents.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL et SUPABASE_KEY doivent être définis dans le .env"
        )

    supabase: Client = create_client(url, key)
    collection = get_collection()

    deja_presents = set(collection.get(include=[])["ids"])
    if verbose:
        print(f"[ChromaDB] {len(deja_presents)} documents déjà indexés.")

    total_supabase = 0
    total_indexe   = 0
    offset         = 0

    while True:
        response = (
            supabase.table("annonces")
            .select(_SELECT_COLONNES)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        batch = response.data
        if not batch:
            break

        total_supabase += len(batch)

        nouveaux = [
            a for a in batch
            if _build_chroma_id(a) not in deja_presents
        ]

        if nouveaux:
            indexes = indexer_annonces(nouveaux)
            total_indexe += indexes
            for a in nouveaux:
                deja_presents.add(_build_chroma_id(a))

        if verbose:
            print(
                f"  Page {offset // page_size + 1} : "
                f"{len(batch)} lus, {len(nouveaux)} nouveaux indexés."
            )

        if len(batch) < page_size:
            break

        offset += page_size

    rapport = {
        "total_supabase": total_supabase,
        "total_indexe":   total_indexe,
        "deja_presents":  len(deja_presents) - total_indexe,
    }

    if verbose:
        print(
            f"\n[Résultat] {total_supabase} annonces lues, "
            f"{total_indexe} nouvelles indexées dans ChromaDB."
        )

    return rapport


# ── Recherche sémantique ──────────────────────────────────────────────────────

def search_similar(
    query: str,
    n_results: int = 5,
    filtre_meta: dict | None = None,
) -> list[dict]:
    """
    Recherche sémantique : retourne les n biens les plus proches de la requête.

    Args:
        query:        description en langage naturel du bien recherché.
        n_results:    nombre de résultats à retourner (défaut 5).
        filtre_meta:  filtres ChromaDB where (opérateurs $eq, $gte, $lte, $and…).
                      Exemples :
                        {"quartier": {"$eq": "Mourillon"}}
                        {"prix": {"$lte": 250000}}
                        {"$and": [{"prix": {"$lte": 380000}}, {"nb_pieces": {"$gte": 3}}]}

    Returns:
        Liste de dicts : id, document, distance + toutes les métadonnées.
        Liste vide si la collection est vide.
    """
    collection = get_collection()

    if collection.count() == 0:
        logger.warning("search_similar() : collection ChromaDB vide.")
        return []

    kwargs: dict = {
        "query_texts": [query],
        "n_results":   min(n_results, collection.count()),
        "include":     ["documents", "metadatas", "distances"],
    }
    if filtre_meta:
        kwargs["where"] = filtre_meta

    results = collection.query(**kwargs)

    ids       = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "id":       ids[i],
            "document": documents[i],
            "distance": round(distances[i], 4),
            **metadatas[i],
        }
        for i in range(len(ids))
    ]


# ── Point d'entrée CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 60)
    print("NidBuyer V2 - Indexation ChromaDB depuis Supabase")
    print("=" * 60)

    try:
        rapport = indexer_depuis_supabase(verbose=True)
    except EnvironmentError as e:
        print(f"\n[ERREUR] {e}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "-" * 60)
    print("Test de recherche semantique...")
    requete_test = "appartement avec terrasse proche mer Toulon"
    resultats = search_similar(requete_test, n_results=3)

    if resultats:
        print(f'\nRequete : "{requete_test}"\n')
        for i, r in enumerate(resultats, 1):
            print(
                f"  #{i}  distance={r['distance']}  "
                f"{r.get('type_bien', '?')} - "
                f"{r.get('surface', '?')} m2 - "
                f"{r.get('prix', '?')} euros - "
                f"{r.get('quartier', '?')}  DPE:{r.get('dpe', '?')}"
            )
            print(f"       Lien : {r.get('lien', 'n/a')}\n")
    else:
        print("  Aucun résultat (collection vide ?).")

    print("=" * 60)
    print("Pipeline RAG opérationnel.")
