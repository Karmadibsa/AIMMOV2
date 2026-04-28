# NidBuyer V2 — Guide de déploiement

## Sommaire

1. [Environnement local](#1-environnement-local)
2. [Backend sur Render](#2-backend-sur-render)
3. [Frontend sur Streamlit Cloud](#3-frontend-sur-streamlit-cloud)
4. [Variables d'environnement](#4-variables-denvironnement)
5. [Vérification post-déploiement](#5-vérification-post-déploiement)

---

## 1. Environnement local

### Prérequis
- Python 3.11+
- Un compte [Supabase](https://supabase.com) avec la table `annonces` créée
- Une clé [Google AI Studio](https://aistudio.google.com) (Gemini / Gemma)

### Installation

```bash
# Depuis la racine du projet (AIMMOV2/)
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration `.env`

Copiez `.env.example` en `.env` et renseignez vos vraies clés :

```bash
cp .env.example .env
```

```dotenv
GEMINI_API_KEY=AIzaSy...
GEMMA_MODEL=gemma-4-27b-it
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJhbGci...   # clé service_role (pas anon)
BACKEND_URL=http://localhost:8000
```

> **Important** : n'ajoutez jamais le fichier `.env` à Git. Vérifiez qu'il est dans `.gitignore`.

### Démarrage local

```bash
# Terminal 1 — Backend FastAPI
cd AIMMOV2
uvicorn backend.main:app --reload

# Terminal 2 — Frontend Streamlit
cd AIMMOV2
streamlit run frontend/app.py
```

Ou utilisez le lanceur Windows :

```bash
run_nidbuyer.bat
```

### Indexation initiale ChromaDB

Si votre base ChromaDB est vide, lancez l'indexation depuis Supabase :

```bash
cd AIMMOV2
python -m backend.rag
```

---

## 2. Backend sur Render

### Déploiement via Dockerfile

1. Créez un **nouveau Web Service** sur [render.com](https://render.com)
2. Connectez votre dépôt GitHub
3. Paramètres du service :

| Champ | Valeur |
|---|---|
| **Environment** | Docker |
| **Dockerfile Path** | `AIMMOV2/Dockerfile` |
| **Root Directory** | `AIMMOV2` |
| **Instance Type** | Free (512 MB RAM) ou Starter |

> Le `Dockerfile` utilise `${PORT:-8000}` — Render injecte `$PORT` automatiquement.

4. Dans **Environment Variables**, ajoutez :

| Variable | Valeur |
|---|---|
| `GEMINI_API_KEY` | Votre clé Google AI Studio |
| `GEMMA_MODEL` | `gemma-4-27b-it` |
| `SUPABASE_URL` | URL de votre projet Supabase |
| `SUPABASE_KEY` | Clé `service_role` Supabase |
| `ALLOWED_ORIGINS` | `https://your-app.streamlit.app` (après déploiement frontend) |

5. Cliquez **Deploy** — l'URL sera du type `https://nidbuyer-api.onrender.com`

### Note sur ChromaDB en production

ChromaDB persiste dans `/app/chroma_db` à l'intérieur du conteneur. Sur Render Free tier, ce stockage est **éphémère** (perdu au redémarrage). Pour la production :
- Utilisez un **Render Disk** (volume persistant, payant)
- Ou remplacez ChromaDB par une solution externe (Pinecone, Weaviate)

---

## 3. Frontend sur Streamlit Cloud

1. Poussez votre code sur GitHub (branche `main`)
2. Connectez-vous sur [share.streamlit.io](https://share.streamlit.io)
3. **New app** :

| Champ | Valeur |
|---|---|
| **Repository** | `votre-org/votre-repo` |
| **Branch** | `main` |
| **Main file path** | `AIMMOV2/frontend/app.py` |

4. Dans **Advanced settings → Secrets**, ajoutez au format TOML :

```toml
BACKEND_URL = "https://nidbuyer-api.onrender.com"
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJhbGci..."
GEMINI_API_KEY = "AIzaSy..."
```

5. Cliquez **Deploy** — l'URL sera du type `https://nidbuyer.streamlit.app`

6. **Dernière étape** : revenez sur Render et mettez à jour `ALLOWED_ORIGINS` avec cette URL Streamlit exacte.

---

## 4. Variables d'environnement

### Tableau récapitulatif

| Variable | Local | Render | Streamlit Cloud | Description |
|---|:---:|:---:|:---:|---|
| `GEMINI_API_KEY` | ✅ | ✅ | ✅ | Clé Google AI Studio (Gemini + Gemma) |
| `GEMMA_MODEL` | ✅ | ✅ | — | Nom du modèle Gemma (défaut : `gemma-4-27b-it`) |
| `SUPABASE_URL` | ✅ | ✅ | ✅ | URL du projet Supabase |
| `SUPABASE_KEY` | ✅ | ✅ | ✅ | Clé `service_role` (bypasse le RLS) |
| `BACKEND_URL` | — | — | ✅ | URL publique du backend Render |
| `ALLOWED_ORIGINS` | — | ✅ | — | Origines CORS autorisées (URL Streamlit) |
| `CHROMA_PATH` | — | — | — | Chemin ChromaDB (défaut : `./chroma_db`) |

> **Sécurité** : utilisez toujours la clé `service_role` pour `SUPABASE_KEY` côté backend (lecture/écriture sans RLS). Ne l'exposez jamais côté client (navigateur).

---

## 5. Vérification post-déploiement

### Backend (Render)

```bash
# Vérifier que l'API répond
curl https://nidbuyer-api.onrender.com/docs
curl https://nidbuyer-api.onrender.com/admin/status

# Tester le chat
curl -X POST https://nidbuyer-api.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Je cherche un T3 à Toulon pour 250k€", "history": []}'
```

### Frontend (Streamlit Cloud)

- Ouvrez l'URL Streamlit dans votre navigateur
- Vérifiez que les annonces se chargent (KPIs en haut)
- Testez l'onglet **Assistant IA** avec une question simple
- Ouvrez les DevTools → onglet Network → vérifiez qu'aucune erreur CORS n'apparaît

### Tests GitHub Actions

```bash
# Lancer localement avant de pusher
cd AIMMOV2
pytest tests/ -v --ignore=tests/test_vision.py
```

La CI vérifie automatiquement à chaque push :
- ✅ Présence des fichiers obligatoires
- ✅ Tests de scoring (backend/scoring.py)
- ✅ Tests RAG (ChromaDB sans API externe)
- ✅ Démarrage de l'API + /docs + /admin/status
- ✅ URL déployée dans README.md répond en HTTP 200
