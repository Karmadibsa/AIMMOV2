"""
Alertes acheteur : notifie par email ou Slack quand un nouveau bien
correspond à un profil enregistré.
"""
import os
import json
from pathlib import Path

PROFILES_FILE = Path("data/alertes.json")


def charger_profils() -> list[dict]:
    if not PROFILES_FILE.exists():
        return []
    return json.loads(PROFILES_FILE.read_text())


def sauvegarder_profil(email: str, profil: dict) -> None:
    profils = charger_profils()
    profils.append({"email": email, "profil": profil})
    PROFILES_FILE.parent.mkdir(exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(profils, ensure_ascii=False, indent=2))


def notifier_email(email: str, biens: list[dict]) -> None:
    """Envoie un email avec les nouveaux biens correspondants."""
    # TODO : utiliser smtplib avec les variables SMTP_* du .env
    raise NotImplementedError


def notifier_slack(webhook_url: str, biens: list[dict]) -> None:
    """Envoie un message Slack avec les nouveaux biens."""
    # TODO : POST sur le webhook avec un message formaté
    raise NotImplementedError


def verifier_nouveaux_biens(nouveaux_biens: list[dict]) -> None:
    """
    Pour chaque profil enregistré, vérifie si un nouveau bien correspond
    et déclenche la notification appropriée.
    """
    # TODO : pour chaque profil, filtrer les biens et appeler notifier_*
    raise NotImplementedError
