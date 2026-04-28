"""
Service Gmail API pour envoyer des emails sécurisés et scalables.

Utilise OAuth2 avec REFRESH_TOKEN au lieu de SMTP classique.
"""
import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


def get_gmail_service():
    """
    Crée une connexion authentifiée à Gmail API.
    
    Le REFRESH_TOKEN se renouvelle automatiquement.
    Requiert les variables d'env:
    - GMAIL_CLIENT_ID
    - GMAIL_CLIENT_SECRET
    - GMAIL_REFRESH_TOKEN
    """
    try:
        creds = Credentials(
            token=None,
            refresh_token=os.environ.get("GMAIL_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GMAIL_CLIENT_ID"),
            client_secret=os.environ.get("GMAIL_CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/gmail.send"]
        )
        
        service = build("gmail", "v1", credentials=creds)
        return service
    
    except Exception as e:
        logger.error(f"❌ Erreur connexion Gmail API: {e}")
        raise


def envoyer_email_gmail(
    destinataire: str,
    sujet: str,
    contenu_html: str,
    contenu_texte: str = None
) -> bool:
    """
    Envoie un email via Gmail API.
    
    Args:
        destinataire: email du destinataire
        sujet: titre de l'email
        contenu_html: contenu en HTML
        contenu_texte: contenu en texte brut (optionnel, fallback)
    
    Returns:
        True si succès, False sinon
    """
    try:
        service = get_gmail_service()
        gmail_email = os.environ.get("GMAIL_EMAIL", "projectaimmo@gmail.com")
        
        # Construction du message
        message = MIMEMultipart("alternative")
        message["to"] = destinataire
        message["from"] = gmail_email
        message["subject"] = sujet
        
        # Ajoute le contenu texte (fallback)
        if contenu_texte:
            message.attach(MIMEText(contenu_texte, "plain"))
        
        # Ajoute le contenu HTML (principal)
        message.attach(MIMEText(contenu_html, "html"))
        
        # Encode en base64 pour Gmail API
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Envoie via Gmail API
        send_message = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()
        
        logger.info(f"✉️ Email Gmail envoyé à {destinataire} (message_id: {send_message.get('id')})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Erreur envoi Gmail API à {destinataire}: {e}")
        return False


def envoyer_email_batch(
    destinataires: list[str],
    sujet: str,
    contenu_html: str,
    contenu_texte: str = None
) -> dict:
    """
    Envoie un email à plusieurs destinataires.
    
    Returns:
        dict avec "success" et "failed" (liste des emails)
    """
    resultats = {"success": [], "failed": []}
    
    for email in destinataires:
        try:
            if envoyer_email_gmail(email, sujet, contenu_html, contenu_texte):
                resultats["success"].append(email)
            else:
                resultats["failed"].append(email)
        except Exception as e:
            logger.error(f"Erreur batch {email}: {e}")
            resultats["failed"].append(email)
    
    return resultats
