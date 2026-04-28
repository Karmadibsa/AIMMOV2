"""Tests unitaires — module RAG"""
import pytest
import chromadb
from backend.rag import indexer_annonces, search_similar


ANNONCES_SAMPLE = [
    {
        "id": "001",
        "type_bien": "Appartement",
        "surface": 68,
        "quartier": "Mourillon",
        "prix": 215_000,
        "description": "Bel appartement lumineux, balcon vue mer partielle, cuisine rénovée.",
        "dpe": "C",
        "pieces": 3,
    },
    {
        "id": "002",
        "type_bien": "Appartement",
        "surface": 45,
        "quartier": "Cap Brun",
        "prix": 180_000,
        "description": "Studio lumineux proche plage, idéal investissement locatif.",
        "dpe": "D",
        "pieces": 2,
    },
    {
        "id": "003",
        "type_bien": "Appartement",
        "surface": 95,
        "quartier": "Mourillon",
        "prix": 350_000,
        "description": "Grand appartement familial, 4 chambres, parking sous-sol.",
        "dpe": "B",
        "pieces": 4,
    },
]

# IDs tels que _build_chroma_id() les génère (pas de 'lien' → ann_<id>)
ID_001 = "ann_001"
ID_002 = "ann_002"
ID_003 = "ann_003"


@pytest.fixture(autouse=True)
def setup_index(tmp_path, monkeypatch):
    """
    Remplace le client ChromaDB par un client isolé dans tmp_path.
    Fonctionne avec l'initialisation paresseuse de rag._client :
      - monkeypatch.setenv() est lu par _get_client() au premier appel
      - monkeypatch.setattr() remet _client à None pour forcer la recréation
    """
    from backend import rag

    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma_test"))
    monkeypatch.setattr(rag, "_client", None)   # force _get_client() à recréer
    monkeypatch.setattr(rag, "_ef", None)       # force _get_ef() à recréer

    indexer_annonces(ANNONCES_SAMPLE)


def test_search_retourne_resultats():
    results = search_similar("appartement vue mer Mourillon", n_results=2)
    assert len(results) == 2


def test_search_pertinence_famille():
    """Une recherche famille doit inclure le T4 dans les résultats."""
    results = search_similar("grand appartement familial 4 chambres", n_results=2)
    ids = [r["id"] for r in results]
    assert ID_003 in ids, f"T4 familial (ann_003) attendu dans {ids}"


def test_search_pertinence_investissement():
    """Une recherche investissement locatif doit inclure le studio T2."""
    results = search_similar("studio investissement locatif rentable", n_results=2)
    ids = [r["id"] for r in results]
    assert ID_002 in ids, f"Studio (ann_002) attendu dans {ids}"
