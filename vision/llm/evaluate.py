import os
from pathlib import Path
from google import genai
from PIL import Image

def evaluer_photos_gemini(photos: list, model_name: str = "gemma-4-26b-a4b-it") -> str:
    """
    Analyse une liste de photos (chemins locaux) via le modèle de vision Gemini.
    Limite le traitement à 4 photos pour des raisons de coûts.
    """
    # Configuration de l'API avec la clé du fichier .env
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("La variable d'environnement GEMINI_API_KEY n'est pas définie dans .env")
    
    # Initialisation du nouveau client
    client = genai.Client(api_key=api_key)
    
    prompt = "Voici plusieurs photos d'un bien immobilier. Analyse son état général, identifie les points forts et les éventuels travaux ou défauts visibles. Synthétise ton analyse."
    
    # Préparation du contenu (texte + images)
    content = [prompt]
    
    # Limiter à 4 images
    for photo_path in photos[:4]:
        try:
            # Gemini accepte directement les objets PIL.Image
            img = Image.open(photo_path)
            content.append(img)
        except Exception as e:
            print(f"Erreur lors du chargement de l'image {photo_path}: {e}")

    try:
        # Appel à l'API avec la nouvelle syntaxe
        response = client.models.generate_content(
            model=model_name,
            contents=content
        )
        return response.text
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API Gemini: {e}")
        return ""

if __name__ == "__main__":
    from dotenv import load_dotenv
    
    # recherche du .env 
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)
    
    # Mettez un chemin d'image valide pour tester
    # Assurez-vous que l'image existe bien à cet endroit
    chemin_image = Path(__file__).resolve().parents[1] / "img" / "cuisine-rénover.webp"
    
    images_de_test = [str(chemin_image)]
    
    print(f"Lancement de l'analyse avec l'image : {chemin_image}")
    resultat = evaluer_photos_gemini(images_de_test)
    
    print("\n--- Résultat de l'analyse ---")
    print(resultat)