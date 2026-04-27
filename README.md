[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/37edVT1_)
# NidBuyer — Votre acheteur IA à Toulon

> **Projet 2 — MBA Data & IA 2026**

## Équipe

### Pôle Produit

| Membre | Rôle |
|--------|------|
| Prénom NOM | Lead architecture |
| Prénom NOM | Backend / RAG |
| Prénom NOM | Frontend / UX |
| Prénom NOM | Données / DVF + scoring |
| Prénom NOM | Prompt engineering |

### Pôle R&D Vision

| Membre | Rôle |
|--------|------|
| Prénom NOM | Approche & dataset |
| Prénom NOM | Entraînement / évaluation |

## Demo

URL déployée : **https://TODO**

## Pourquoi NidBuyer ?

|  | BienIci | MeilleursAgents | SeLoger | NidBuyer |
|---|:---:|:---:|:---:|:---:|
| Lister des biens | ✅ | ✅ | ✅ | ✅ |
| Estimer le prix | ❌ | ✅ vendeur | ❌ | ✅ acheteur |
| Détecter sous-évaluations | ❌ | ❌ | ❌ | ✅ |
| Alerter sur profil | ❌ | ❌ | partiel | ✅ |
| Analyser les photos | ❌ | ❌ | ❌ | ✅ |
| Conseiller sur l'offre | ❌ | ❌ | ❌ | ✅ |

## Lancer en local

```bash
cp .env.example .env
# Remplir les variables dans .env (voir section Configuration)

pip install -r requirements.txt

# Backend
uvicorn backend.main:app --reload

# Frontend (autre terminal)
streamlit run frontend/app.py
```

## Configuration

Copier `.env.example` → `.env` et remplir :

| Variable | Obligatoire | Description |
|---|:---:|---|
| `ANTHROPIC_API_KEY` | ✅ | Clé API Claude |
| `SUPABASE_URL` | ✅ | URL du projet Supabase |
| `SUPABASE_KEY` | ✅ | Clé anon/service Supabase |
| `SMTP_HOST` / `SMTP_USER` / ... | ➕ | Alertes email |
| `SLACK_WEBHOOK_URL` | ➕ | Alertes Slack |

## Architecture

```
nidbuyer/
├── backend/
│   ├── main.py        # FastAPI + scheduler ingestion 7h00
│   ├── rag.py         # ChromaDB — recherche vectorielle
│   ├── scoring.py     # Score opportunité vs médiane DVF
│   ├── ingestion.py   # Scraper → Supabase → ChromaDB
│   ├── alert.py       # Alertes email / Slack
│   └── sources/       # BienIci · LeBonCoin · Générique LLM · ...
├── frontend/          # Streamlit — interface acheteur
├── vision/            # R&D : CNN ou LLM multimodal
│   ├── model.py       # Interface commune (appelée par scoring.py)
│   ├── cnn/           # Piste CNN
│   ├── llm/           # Piste LLM multimodal
│   ├── APPROACH.md    # Choix justifié + résultats mesurés
│   └── benchmark.py   # Script de comparaison
├── prompts/           # System prompts + EXPERIMENTS.md
├── tests/             # Tests scoring, RAG, vision
└── .env               # SUPABASE_URL · SUPABASE_KEY · ANTHROPIC_API_KEY · ...
```

**Les annonces ne transitent pas par GitHub.** Le pipeline écrit directement dans deux bases externes :

```
Scraper (quotidien 7h00)
        ↓
Supabase PostgreSQL   ← données brutes structurées
        ↓
ChromaDB (Railway / HF)  ← vecteurs pour le RAG
        ↓
FastAPI + Streamlit   ← interface acheteur déployée
```

> **Pourquoi pas un CSV dans le repo ?** Les annonces sont des données vivantes — un `git commit` par ingestion n'est pas une pratique prod. GitHub est pour le code ; Supabase est pour la data.

## Tâche J1

**Avant la fin du premier jour :**

1. Importer les annonces P1 dans Supabase (table `annonces`) et lancer une première indexation ChromaDB
2. Vérifier le compte : `GET /admin/status` — si < 300 annonces → scraper immédiatement
3. Lancer `POST /admin/sync` pour valider le pipeline de bout en bout
4. Déclarer les rôles dans ce README et pousser

> *"Vos données P1 sont la fondation. Sans elles, pas de RAG."*

Nombre d'annonces indexées dans la base RAG : **XXX** ← *à mettre à jour J1*

## Prompt Engineering

Voir [`prompts/EXPERIMENTS.md`](prompts/EXPERIMENTS.md) — 3 versions comparées sur le même bien de référence.

## R&D Vision

Voir [`vision/APPROACH.md`](vision/APPROACH.md) — approche retenue, métriques, limites.
