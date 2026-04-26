# R&D Vision — Choix d'approche et résultats

## Approche retenue

**CNN / LLM multimodal / Autre** *(barrer les mentions inutiles)*

Modèle : _______________

Justification du choix :
- Pourquoi cette approche plutôt que l'alternative ?
- Contraintes prises en compte (données disponibles, coût, temps) :

---

## Dataset

| | Valeur |
|--|--|
| Nombre de photos labellisées | |
| Source des photos | |
| Répartition par classe | excellent: X / bon: X / correct: X / à rénover: X |

*(Si LLM : indiquer "aucun label nécessaire" et le nombre de photos testées)*

---

## Résultats

### Métriques sur jeu de test

| Classe | Précision | Rappel | F1 |
|--------|-----------|--------|----|
| excellent | | | |
| bon | | | |
| correct | | | |
| a_renover | | | |

**Accuracy globale :** ____%

### Exemples de prédictions

| Photo | Vérité terrain | Prédiction | Correct ? |
|-------|---------------|------------|-----------|
| photo_001.jpg | a_renover | a_renover | ✓ |
| photo_002.jpg | bon | correct | ✗ |

---

## Coût

*(Si LLM uniquement)*

| Modèle testé | Coût / photo | Coût total tests | Qualité estimée |
|-------------|-------------|-----------------|----------------|
| | | | |

---

## Limites et biais

- Ce que le modèle rate systématiquement :
- Conditions où il se trompe :
- Ce qu'on ferait différemment avec plus de temps :

---

## Intégration dans le scoring

La fonction `vision.model.evaluer_etat_bien()` est appelée dans `backend/scoring.py`
via le paramètre `vision_result`. Impact sur le score d'opportunité :

- Profil investisseur : travaux = opportunité → malus = 0
- Profil RP famille : travaux = frein → malus = 0.3
