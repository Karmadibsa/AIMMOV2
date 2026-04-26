"""
Sources d'annonces disponibles.

Pour ajouter une source :
1. Créer un fichier dans ce dossier (ex: maseloger.py)
2. Hériter de SourceBase et implémenter fetch_new()
3. L'importer ici et l'ajouter à SOURCES_ACTIVES

Seules les sources dans SOURCES_ACTIVES sont appelées lors de l'ingestion quotidienne.
"""
from .bienici import BienIciSource
from .leboncoin import LeBonCoinSource
from .generique import SourceGenerique

# Activer/désactiver les sources ici
SOURCES_ACTIVES: list = [
    # BienIciSource(),
    # LeBonCoinSource(),
    # SourceGenerique(),
]
