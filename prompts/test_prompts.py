import os
from google.generativeai import GenerativeModel, configure

# Config API
configure(api_key=os.getenv("GEMINI_API_KEY"))

model = GenerativeModel(os.getenv("GEMMA_MODEL"))

# Charger les prompts
with open("prompts/system.txt") as f:
    system_prompt = f.read()

with open("prompts/fiche_decision_v3.txt") as f:
    user_prompt = f.read()

# Données de test (ton bien de référence)
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
response = model.generate_content(
    system_prompt + "\n\n" + final_prompt
)

print(response.text)