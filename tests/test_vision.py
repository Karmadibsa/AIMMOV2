"""Tests unitaires — module Vision (géré par l'équipe Vision)."""
import pytest

# Le module vision/ est développé par les collègues Vision.
# Ces tests sont skippés en CI jusqu'à intégration complète.
pytestmark = pytest.mark.skip(reason="vision.model non intégré dans ce repo — module équipe Vision")


from vision.model import evaluer_etat_bien  # noqa: E402 — importé après le skip

CHAMPS_ATTENDUS   = {"etat_general", "travaux_detectes", "estimation_travaux", "luminosite", "score_presentation"}
ETATS_VALIDES     = {"excellent", "bon", "correct", "a_renover"}
ESTIMATIONS_VALIDES = {"0-5k", "5-20k", "20-50k", ">50k"}


def test_retourne_les_bons_champs(photo_test):
    result = evaluer_etat_bien([photo_test])
    assert CHAMPS_ATTENDUS.issubset(result.keys())


def test_etat_general_valide(photo_test):
    result = evaluer_etat_bien([photo_test])
    assert result["etat_general"] in ETATS_VALIDES


def test_estimation_travaux_valide(photo_test):
    result = evaluer_etat_bien([photo_test])
    assert result["estimation_travaux"] in ESTIMATIONS_VALIDES


def test_luminosite_dans_plage(photo_test):
    result = evaluer_etat_bien([photo_test])
    assert 1 <= result["luminosite"] <= 5


def test_score_presentation_dans_plage(photo_test):
    result = evaluer_etat_bien([photo_test])
    assert 1 <= result["score_presentation"] <= 10


def test_photos_vide_leve_erreur():
    with pytest.raises(ValueError):
        evaluer_etat_bien([])


@pytest.fixture
def photo_test():
    return "tests/fixtures/photo_test.jpg"
