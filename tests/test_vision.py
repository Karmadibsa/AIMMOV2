"""Tests unitaires — module Vision"""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from vision.model import evaluer_etat_bien

# Charge le .env à la racine du projet pour récupérer GEMINI_API_KEY localement
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

CHAMPS_ATTENDUS = {"etat_general", "travaux_detectes", "estimation_travaux", "luminosite", "score_presentation"}
ETATS_VALIDES = {"excellent", "bon", "correct", "a_renover"}
ESTIMATIONS_VALIDES = {"0-5k", "5-20k", "20-50k", ">50k"}

# Skip automatique si pas de clé API (tests d'intégration appellent Gemini en réel)
_HAS_API_KEY = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
requires_gemini = pytest.mark.skipif(
    not _HAS_API_KEY,
    reason="GEMINI_API_KEY absent — tests d'intégration Gemini désactivés.",
)


@pytest.fixture(scope="module")
def photo_test():
    """Image de test embarquée dans le repo (cuisine à rénover)."""
    p = Path(__file__).resolve().parent / "img" / "cuisine-rénover.webp"
    if not p.is_file():
        pytest.skip(f"Image de test introuvable : {p}")
    return str(p)


@pytest.fixture(scope="module")
def vision_result(photo_test):
    """Mutualise un seul appel Gemini pour tous les tests d'un module."""
    return evaluer_etat_bien([photo_test])


@requires_gemini
def test_retourne_les_bons_champs(vision_result):
    assert CHAMPS_ATTENDUS.issubset(vision_result.keys()), \
        f"Champs manquants : {CHAMPS_ATTENDUS - vision_result.keys()}"


@requires_gemini
def test_etat_general_valide(vision_result):
    assert vision_result["etat_general"] in ETATS_VALIDES


@requires_gemini
def test_estimation_travaux_valide(vision_result):
    assert vision_result["estimation_travaux"] in ESTIMATIONS_VALIDES


@requires_gemini
def test_luminosite_dans_plage(vision_result):
    assert 1 <= vision_result["luminosite"] <= 5


@requires_gemini
def test_score_presentation_dans_plage(vision_result):
    assert 1 <= vision_result["score_presentation"] <= 10


@requires_gemini
def test_travaux_detectes_est_une_liste(vision_result):
    assert isinstance(vision_result["travaux_detectes"], list)


def test_photos_vide_leve_erreur():
    """Test pur (pas d'appel Gemini) — vérifie le contrat d'erreur."""
    with pytest.raises(ValueError):
        evaluer_etat_bien([])
