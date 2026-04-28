import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Charger le .env
load_dotenv()

# Config API
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Modèle — on met une valeur par défaut si GEMMA_MODEL est vide
model_name = os.getenv("GEMMA_MODEL", "gemini-2.0-flash")

# Charger les prompts
with open("prompts/system.txt") as f:
    system_prompt = f.read()

with open("prompts/fiche_decision_v3.txt") as f:
    user_prompt = f.read()

# Données de test (bien de référence)
fiche = """
T3, 68m², Mourillon
Prix : 215000€
Prix/m² : 3162€
Médiane quartier : 3400€
Écart : -7%
"""

description = """
Bel appartement lumineux, cuisine rénovée, balcon vue mer partielle, proximité plage du Mourillon.
"""

profil = "Investisseur locatif"

# Injecter les variables
final_prompt = user_prompt.format(
    fiche_structuree=fiche,
    description_annonce=description,
    profil=profil
)

# Appel modèle
response = client.models.generate_content(
    model=model_name,
    config=types.GenerateContentConfig(system_instruction=system_prompt),
    contents=final_prompt
)

print(response.text)