"""
Indexation et recherche sémantique sur les annonces immobilières.
Utilise ChromaDB comme base vectorielle.
"""
import chromadb
from chromadb.utils import embedding_functions


# TODO : choisir le modèle d'embedding (all-MiniLM-L6-v2, text-embedding-3-small, etc.)
# Justifier votre choix dans le README (vitesse vs qualité, coût, langue)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client = chromadb.PersistentClient(path="./chroma_db")
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def get_collection():
    return _client.get_or_create_collection(
        name="annonces_toulon",
        embedding_function=_ef,
    )


def indexer_annonces(annonces: list[dict]) -> None:
    """
    Indexe une liste d'annonces dans ChromaDB.

    Chaque annonce doit contenir au minimum :
    id, type, surface, quartier, prix, description
    """
    collection = get_collection()
    # TODO : construire le texte à encoder et appeler collection.add()
    raise NotImplementedError


def search_similar(query: str, n_results: int = 5, filtre_meta: dict | None = None) -> list[dict]:
    """
    Recherche sémantique : retourne les n_results biens les plus proches de la requête.

    Args:
        query: description en langage naturel du bien recherché
        n_results: nombre de résultats à retourner
        filtre_meta: filtres optionnels sur les métadonnées (ex: {"quartier": "Mourillon"})

    Returns:
        Liste de dicts avec les métadonnées des biens
    """
    collection = get_collection()
    # TODO : appeler collection.query() avec where= si filtre_meta est fourni
    raise NotImplementedError
