"""
Pipeline d'ingestion quotidienne.

Orchestration :
  1. Appelle toutes les sources actives
  2. Déduplique par url_source
  3. Indexe les nouvelles annonces dans ChromaDB
  4. Déclenche les alertes pour les profils correspondants
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from .rag import indexer_annonces, get_collection
from .alert import charger_profils, notifier_email, notifier_slack
from .sources import SOURCES_ACTIVES

logger = logging.getLogger(__name__)

LAST_RUN_FILE = Path("data/.last_sync")


def annonces_deja_indexees() -> set[str]:
    """Retourne les url_source déjà présentes dans ChromaDB."""
    collection = get_collection()
    results = collection.get(include=["metadatas"])
    return {m.get("url_source", "") for m in results["metadatas"] if m.get("url_source")}


def sync(dry_run: bool = False) -> dict:
    """
    Lance la synchronisation complète.

    Args:
        dry_run: si True, scrape et détecte les nouveautés mais n'indexe pas

    Returns:
        Rapport : {"nouvelles": int, "sources": dict, "alertes_envoyees": int, "erreurs": list}
    """
    rapport = {"nouvelles": 0, "sources": {}, "alertes_envoyees": 0, "erreurs": []}
    debut = datetime.now()

    logger.info(f"Sync démarrée — {len(SOURCES_ACTIVES)} source(s) active(s)")

    if not SOURCES_ACTIVES:
        logger.warning("Aucune source active. Activez-en dans backend/sources/__init__.py")
        return rapport

    # 1. Récupérer les URLs déjà indexées
    indexees = annonces_deja_indexees()

    # 2. Scraper toutes les sources
    toutes_annonces = []
    for source in SOURCES_ACTIVES:
        try:
            annonces = source.fetch_new()
            rapport["sources"][source.name] = len(annonces)
            toutes_annonces.extend(annonces)
            logger.info(f"  {source.name} → {len(annonces)} annonces récupérées")
        except NotImplementedError:
            msg = f"{source.name} : fetch_new() non implémenté"
            logger.warning(msg)
            rapport["erreurs"].append(msg)
        except Exception as e:
            msg = f"{source.name} : {e}"
            logger.error(msg)
            rapport["erreurs"].append(msg)

    # 3. Filtrer les nouvelles annonces
    nouvelles = [
        a for a in toutes_annonces
        if a.get("url_source") and a["url_source"] not in indexees
    ]
    # Dédupliquer entre sources
    vues = set()
    nouvelles_uniques = []
    for a in nouvelles:
        if a["url_source"] not in vues:
            vues.add(a["url_source"])
            nouvelles_uniques.append(a)

    rapport["nouvelles"] = len(nouvelles_uniques)
    logger.info(f"{len(nouvelles_uniques)} nouvelles annonces à indexer")

    if dry_run or not nouvelles_uniques:
        return rapport

    # 4. Indexer dans ChromaDB
    try:
        indexer_annonces(nouvelles_uniques)
    except Exception as e:
        rapport["erreurs"].append(f"Indexation : {e}")
        logger.error(f"Erreur indexation : {e}")
        return rapport

    # 5. Alertes : vérifier les profils enregistrés
    profils = charger_profils()
    for profil_entry in profils:
        email = profil_entry.get("email")
        profil = profil_entry.get("profil", {})
        biens_matching = _filtrer_pour_profil(nouvelles_uniques, profil)
        if biens_matching:
            try:
                notifier_email(email, biens_matching)
                rapport["alertes_envoyees"] += 1
            except NotImplementedError:
                pass  # Alertes non encore implémentées
            except Exception as e:
                rapport["erreurs"].append(f"Alerte {email} : {e}")

    LAST_RUN_FILE.write_text(debut.isoformat())
    logger.info(f"Sync terminée en {(datetime.now() - debut).seconds}s — {rapport}")
    return rapport


def _filtrer_pour_profil(annonces: list[dict], profil: dict) -> list[dict]:
    """Filtre grossier avant l'analyse LLM — évite d'appeler le LLM sur tous les biens."""
    budget = profil.get("budget_max")
    surface_min = profil.get("surface_min", 0)
    matching = []
    for a in annonces:
        if budget and a.get("prix") and a["prix"] > budget:
            continue
        if surface_min and a.get("surface") and a["surface"] < surface_min:
            continue
        matching.append(a)
    return matching
