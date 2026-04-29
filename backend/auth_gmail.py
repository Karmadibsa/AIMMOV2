"""
Script de configuration de Gmail API (à lancer une seule fois).

Génère le REFRESH_TOKEN et le stocke dans .env
"""
import os
import webbrowser
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv, dotenv_values
from pathlib import Path

# Charge les variables existantes de .env
load_dotenv()

# Configuration
CLIENT_ID = "REDACTED_GMAIL_CLIENT_ID"
CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "REDACTED_GMAIL_CLIENT_SECRET")
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REDIRECT_URI = "http://localhost:8888/auth_callback"

def get_gmail_auth():
    """
    Crée un flux OAuth2 et génère un REFRESH_TOKEN
    """
    print("🔐 Initialisation de l'authentification Gmail...")
    
    # Config du client
    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8888/auth_callback"]
        }
    }
    
    # Crée le flux OAuth2
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=SCOPES
    )
    
    # Lance le navigateur pour l'authentification
    print("\n🌐 Ouverture du navigateur pour authentification...")
    creds = flow.run_local_server(port=8888)
    
    print("\n✅ Authentification réussie !")
    print(f"\n🔑 Voici ton REFRESH_TOKEN (à copier dans .env):\n")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}\n")
    
    # Optionnel : ajouter directement au .env
    add_to_env = input("Veux-tu que je l'ajoute automatiquement à .env ? (o/n): ").lower()
    
    if add_to_env == "o":
        env_path = Path(".env")
        
        # Lire le contenu actuel
        content = ""
        if env_path.exists():
            content = env_path.read_text()
        
        # Ajouter ou remplacer le REFRESH_TOKEN
        if "GMAIL_REFRESH_TOKEN=" in content:
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if line.startswith("GMAIL_REFRESH_TOKEN="):
                    new_lines.append(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)
        else:
            content += f"\nGMAIL_REFRESH_TOKEN={creds.refresh_token}\n"
        
        env_path.write_text(content)
        print(f"✅ REFRESH_TOKEN ajouté à .env")
    
    return creds


if __name__ == "__main__":
    get_gmail_auth()
    print("\n💡 Tu peux maintenant utiliser Gmail API dans ton backend !")
