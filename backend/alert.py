"""
Alertes acheteur : notifie par email ou Slack quand un nouveau bien
correspond à un profil enregistré.
"""
import os
import json
import smtplib
import logging
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import requests

logger = logging.getLogger(__name__)
PROFILES_FILE = Path("data/alertes.json")


def charger_profils() -> list[dict]:
    if not PROFILES_FILE.exists():
        return []
    return json.loads(PROFILES_FILE.read_text())


def sauvegarder_profil(email: str, nom_alerte: str, profil: dict) -> None:
    """Sauvegarde un profil d'alerte."""
    profils = charger_profils()
    profils.append({
        "email": email,
        "nom_alerte": nom_alerte,
        "profil": profil,
        "created_at": datetime.now().isoformat(),
        "actif": True
    })
    PROFILES_FILE.parent.mkdir(exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(profils, ensure_ascii=False, indent=2))
    logger.info(f"✅ Alerte '{nom_alerte}' enregistrée pour {email}")


def supprimer_profil(email: str, nom_alerte: str) -> bool:
    """Supprime un profil d'alerte."""
    profils = charger_profils()
    profils = [p for p in profils if not (p["email"] == email and p["nom_alerte"] == nom_alerte)]
    PROFILES_FILE.parent.mkdir(exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(profils, ensure_ascii=False, indent=2))
    return True


def filtrer_biens(biens: list[dict], criteres: dict) -> list[dict]:
    """Filtre les biens selon les critères du profil."""
    resultat = biens.copy()

    # Budget max
    if criteres.get("budget_max"):
        resultat = [b for b in resultat if b.get("valeur_fonciere", 0) <= criteres["budget_max"]]

    # Surface min
    if criteres.get("surface_min"):
        resultat = [b for b in resultat if b.get("surface_reelle_bati", 0) >= criteres["surface_min"]]

    # Nombre de pièces
    if criteres.get("nb_pieces_min"):
        resultat = [b for b in resultat if b.get("nombre_pieces_principales", 0) >= criteres["nb_pieces_min"]]

    # Quartiers / communes
    if criteres.get("quartiers"):
        communes_ok = set(criteres["quartiers"])
        resultat = [b for b in resultat if b.get("nom_commune") in communes_ok]

    # Type de bien
    if criteres.get("type_bien") and criteres["type_bien"] != "Tous":
        resultat = [b for b in resultat if b.get("type_bien") == criteres["type_bien"]]

    return resultat


def notifier_email(email: str, nom_alerte: str, biens: list[dict]) -> bool:
    """Envoie un email avec les nouveaux biens correspondants."""
    if not biens:
        logger.info(f"Aucun bien à envoyer pour {email} (alerte: {nom_alerte})")
        return False

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.error("❌ Configuration SMTP incomplète dans .env")
        return False

    try:
        # Construction du message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🏠 NidBuyer Alerte : {nom_alerte} - {len(biens)} bien(s)"
        msg["From"] = smtp_user
        msg["To"] = email

        # HTML body
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2>🏠 NidBuyer - Alerte "{nom_alerte}"</h2>
                <p>{len(biens)} <strong>bien(s)</strong> correspond(ent) à vos critères !</p>
                <hr>
        """

        for bien in biens[:10]:  # Limiter à 10 annonces par email
            prix = bien.get("valeur_fonciere", "N/A")
            titre = bien.get("titre", "Sans titre")
            commune = bien.get("nom_commune", "")
            surface = bien.get("surface_reelle_bati", "N/A")
            url = bien.get("url", "#")
            prix_m2 = bien.get("prix_m2", "N/A")

            html_content += f"""
                <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;">
                    <h3>{titre}</h3>
                    <p><strong>Prix :</strong> {prix:,}€ ({prix_m2}€/m²)</p>
                    <p><strong>Surface :</strong> {surface}m² | <strong>Commune :</strong> {commune}</p>
                    <a href="{url}" style="background-color: #E8714A; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">
                        Voir l'annonce →
                    </a>
                </div>
            """

        html_content += """
                <hr>
                <p style="font-size: 12px; color: #999;">
                    Email automatique de <strong>NidBuyer</strong> - 
                    <a href="https://nidbuyer.aimmo.fr">Gérer vos alertes</a>
                </p>
            </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        # Envoi
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"✉️ Email envoyé à {email} ({len(biens)} biens)")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur envoi email à {email}: {e}")
        return False


def notifier_slack(webhook_url: str, nom_alerte: str, biens: list[dict]) -> bool:
    """Envoie un message Slack avec les nouveaux biens."""
    if not biens or not webhook_url:
        return False

    try:
        # Formater les biens pour Slack
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🏠 Alerte : {nom_alerte}*\n{len(biens)} bien(s) correspond(ent) à vos critères !"
                }
            }
        ]

        for bien in biens[:5]:  # Limiter à 5 biens
            titre = bien.get("titre", "Sans titre")[:60]
            prix = bien.get("valeur_fonciere", "N/A")
            commune = bien.get("nom_commune", "")
            url = bien.get("url", "")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{titre}*\n{prix:,}€ - {commune}\n<{url}|Voir l'annonce>"
                }
            })

        payload = {"blocks": blocks}
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()

        logger.info(f"✅ Message Slack envoyé pour alerte '{nom_alerte}'")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur envoi Slack: {e}")
        return False


def verifier_et_notifier_alertes(nouveaux_biens: list[dict]) -> None:
    """
    Pour chaque profil enregistré, vérifie si un nouveau bien correspond
    et déclenche la notification appropriée.
    
    Cette fonction est appelée quotidiennement à 9h30.
    """
    profils = charger_profils()

    if not profils:
        logger.info("ℹ️ Aucun profil d'alerte enregistré")
        return

    for profil in profils:
        if not profil.get("actif", True):
            continue

        email = profil["email"]
        nom_alerte = profil.get("nom_alerte", "Sans nom")
        criteres = profil["profil"]

        # Filtrer les biens correspondant au profil
        biens_matches = filtrer_biens(nouveaux_biens, criteres)

        if not biens_matches:
            logger.info(f"ℹ️ Aucun bien pour {email} - alerte '{nom_alerte}'")
            continue

        # Envoyer notifications
        notifier_email(email, nom_alerte, biens_matches)

        # Slack optionnel
        slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        if slack_webhook:
            notifier_slack(slack_webhook, nom_alerte, biens_matches)
