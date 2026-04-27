import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Charger la clé depuis le .env à la racine
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Modèles disponibles sur votre compte :")
try:
    # Parcourir et afficher le nom des modèles
    for model in client.models.list():
        print(f"- {model.name}")
except Exception as e:
    print(f"Erreur lors de la récupération des modèles : {e}")