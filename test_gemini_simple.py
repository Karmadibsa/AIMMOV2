import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Charger le .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Clé détectée : {api_key[:10]}...") # Affiche les 10 premiers caractères

# 2. Configurer Gemini
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemma-4-26b-a4b-it')

    # 3. Test d'appel simple
    print("Envoi d'un message de test à Google AI Studio...")
    response = model.generate_content("Dis bonjour et confirme que tu es opérationnel.")
    
    print("\n--- RÉPONSE DE GEMINI ---")
    print(response.text)
    print("-------------------------\n")
    print("✅ Connexion réussie !")

except Exception as e:
    print("\n❌ ERREUR DÉTECTÉE :")
    print(e)