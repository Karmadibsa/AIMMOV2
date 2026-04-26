"""
Source : Bien'ici — annonces immobilières à Toulon.

Bien'ici expose une API JSON non-officielle utilisée par leur site web.
Inspecter les requêtes réseau sur bienici.com pour retrouver les paramètres.
"""
import requests
from .base import SourceBase


class BienIciSource(SourceBase):
    name = "bienici"

    # URL de l'API interne (à vérifier via les DevTools de votre navigateur)
    API_URL = "https://www.bienici.com/realEstateAds.json"

    def fetch_new(self) -> list[dict]:
        # TODO : construire les paramètres de recherche (ville, type, budget...)
        # params = {"filters": json.dumps({...}), "size": 100, "from": 0}
        # response = requests.get(self.API_URL, params=params, headers={"User-Agent": "..."})
        # annonces_brutes = response.json()["realEstateAds"]
        # return [self.normalize(self._parse(a)) for a in annonces_brutes]
        raise NotImplementedError

    def _parse(self, raw: dict) -> dict:
        """Convertit un objet annonce BienIci vers le format standard."""
        return {
            "id_source":   str(raw.get("id", "")),
            "url_source":  f"https://www.bienici.com/annonce/{raw.get('id', '')}",
            "type":        raw.get("roomsQuantity", ""),
            "surface":     raw.get("surfaceArea"),
            "prix":        raw.get("price"),
            "quartier":    raw.get("district", {}).get("name", ""),
            "ville":       raw.get("city", "Toulon"),
            "description": raw.get("description", ""),
            "photos":      [p.get("url", "") for p in raw.get("photos", [])],
            "nb_pieces":   raw.get("roomsQuantity"),
            "dpe":         raw.get("energyClassification"),
        }
