# Journal des expérimentations — Prompt Engineering NidBuyer

## Notre approche : RAG hybride anti-hallucination

### Problème fondamental

Un LLM généraliste, interrogé naïvement sur un bien immobilier, **invente des données de marché** :
> *"Le prix moyen dans le Mourillon est d'environ 3 200 €/m²…"*

Ce chiffre peut être plausible ou totalement faux. Il est invérifiable et non reproductible.
Dans un outil d'aide à la décision d'achat (budget réel, engagement financier de 200–400 k€),
cette hallucination est inacceptable.

### Notre solution : brider le LLM avec les maths

```
Supabase (table annonces)
      │
      ▼
analysis/scoring.py  ← algorithmes from scratch (0 pandas / 0 numpy)
  • médiane €/m² du segment (median() pur Python)
  • écart bien vs marché (score_opportunite())
  • score 0–100
      │
      ▼  données chiffrées validées
llm_advisor.py
  • injecte les calculs dans le prompt utilisateur
  • SYSTEM PROMPT interdit au LLM d'inventer des chiffres
  • LLM rédige l'argumentation, pas l'analyse quantitative
      │
      ▼
Fiche de décision Markdown (3 sections)
```

**Principe clé :** le LLM ne fait que du langage naturel sur des chiffres qu'il n'a pas calculés.
Il argumente, contextualise, et conseille — il ne quantifie pas.

---

## Bien de référence (identique pour les 3 versions)

> **T3, 68 m², Mourillon (Toulon), 215 000 €**
> Description : *"Bel appartement lumineux, cuisine rénovée, balcon vue mer partielle, proximité plage du Mourillon."*
>
> Calculs NidBuyer (from scratch sur DVF Supabase) :
> - Médiane quartier : **3 400 €/m²**
> - Prix bien : **3 162 €/m²**
> - Écart : **-7,0 %** → *Bonne affaire*
> - Score : **57/100**
> - Profil : **RP** (Résidence Principale, budget max 380 000 €)

---

## V1 — Prompt basique (sans injection de données)

```
Tu es un expert immobilier à Toulon.
Analyse ce bien et dis-moi si c'est une bonne affaire :
T3, 68 m², quartier Mourillon, prix 215 000 €.
Description : "Bel appartement lumineux, cuisine rénovée, balcon vue mer partielle."
```

**Réponse obtenue :**

> *"Ce T3 dans le Mourillon semble attractif. Le prix de 215 000 € pour 68 m² représente environ
> 3 160 €/m², ce qui est dans la moyenne des biens de ce quartier (généralement entre 3 000 et
> 3 800 €/m²). La cuisine rénovée est un vrai plus. Je vous recommande de vérifier les charges
> de copropriété et de faire une offre aux alentours de 210 000 €."*

**Analyse :**
- Ce qui fonctionne : structure naturelle, ton accessible.
- Ce qui manque : le LLM invente la fourchette "3 000–3 800 €/m²" sans source. Aucune contrainte
  de format. Pas de persona. Réponse non reproductible d'un appel à l'autre.

---

## V2 — Format structuré (sans données injectées)

```
Tu es NidBuyer, expert immobilier spécialisé sur Toulon.
Analyse ce bien pour un acheteur en résidence principale (budget max 380 000 €).

Bien : T3, 68 m², Mourillon, 215 000 €
Description : "Bel appartement lumineux, cuisine rénovée, balcon vue mer partielle."

Réponds en 3 sections Markdown :
### 1. Opportunité
### 2. Risques
### 3. Conseil de négociation
```

**Réponse obtenue :**

> ### 1. Opportunité
> *"Le Mourillon est l'un des quartiers les plus recherchés de Toulon. À 215 000 €, ce T3
> se situe légèrement sous les prix habituels du secteur (estimés autour de 230–250 k€ pour
> ce type de bien), ce qui en fait une opportunité intéressante pour une résidence principale."*
>
> ### 2. Risques
> *"Vérifier le DPE, les charges de copropriété et l'état de la toiture. La vue mer 'partielle'
> mérite une visite à différentes heures."*
>
> ### 3. Conseil de négociation
> *"Offrir 205 000 € en première approche, le marché vous est favorable."*

**Analyse :**
- Ce qui s'est amélioré : format garanti, persona pris en compte, ton professionnel.
- Ce qui reste perfectible : le LLM invente toujours "230–250 k€" sans source. L'offre à
  205 000 € est arbitraire. Aucun lien entre la réponse et nos calculs mathématiques réels.

---

## V3 — Injection des données + contrainte anti-hallucination ✅ (production)

```
[SYSTEM]
Tu es NidBuyer, expert immobilier spécialisé sur Toulon et le Var.
Tu es direct, analytique et pragmatique. Ton rôle est d'aider des acheteurs
à prendre une décision rapide et éclairée.

RÈGLES ABSOLUES :
1. Tu ne cites QUE les chiffres fournis dans le message utilisateur
   (prix, surface, écart marché, médiane). Tu n'inventes aucune donnée de marché.
2. Si une information clé manque (DPE, charges copro…), tu le signales
   sans substituer une valeur fictive.
3. Tu rédiges en français, de façon concise et professionnelle.
4. Ta réponse est TOUJOURS structurée en exactement 3 sections Markdown :
   ### 1. Opportunité / ### 2. Risques / ### 3. Conseil de négociation
   Pas d'introduction. Pas de conclusion. Directement les 3 sections.

[USER]
## Bien à analyser
- Titre    : Appartement T3 Mourillon vue mer
- Commune  : Toulon
- Surface  : 68.0 m²  |  3.0 pièces
- Prix     : 215 000 €
- Description (extrait) : Appartement — 68 m² — 3 pièces — à Toulon — 215 000 €
  — Bel appartement lumineux, cuisine rénovée, balcon vue mer partielle, proximité plage du Mourillon.

## Validation mathématique (algorithmes NidBuyer — données DVF Supabase)
- Prix au m²            : 3 162 €/m²
- Médiane marché local  : 3 400 €/m²
- Écart au marché       : -7,0 %  →  Bonne affaire
- Score opportunité     : 57/100

## Profil acheteur ciblé
- Profil  : Résidence Principale  (rp)
- Budget  : 380 000 €

Génère maintenant la fiche de décision (### 1. Opportunité / ### 2. Risques
/ ### 3. Conseil de négociation).
Cite les chiffres fournis ci-dessus. 2-3 phrases par section, pas davantage.
```

**Réponse obtenue (exemple représentatif) :**

> ### 1. Opportunité
> Ce T3 de 68 m² s'affiche à **3 162 €/m²**, soit **-7 %** sous la médiane DVF du marché local
> (3 400 €/m²), confirmant une *bonne affaire* selon nos calculs (score 57/100). Pour un profil
> résidence principale avec un budget de 380 000 €, le prix de 215 000 € laisse une marge confortable.
> La cuisine rénovée réduit le budget travaux immédiats.
>
> ### 2. Risques
> - **DPE non mentionné** — à exiger avant toute offre (impact sur les charges et la revente).
> - **Copropriété** : vérifier les charges, le carnet d'entretien et les travaux votés en AG.
> - "Vue mer partielle" : visite obligatoire à plusieurs heures pour valider luminosité et nuisances.
>
> ### 3. Conseil de négociation
> L'écart de -7 % valide une offre ferme à **210 000 €** (-2,3 % sur le prix affiché),
> justifiée par l'absence d'information sur le DPE. Si le vendeur refuse, **212 500 €** reste
> raisonnable. Ne pas dépasser le prix affiché : la donnée DVF vous est favorable.

**Analyse — pourquoi V3 > V1 et V2 :**
- Tous les chiffres cités sont traçables (issus de `scoring.py`, pas du LLM).
- La règle absolue n°1 empêche l'invention de fourchettes de prix.
- Le format est garanti par la contrainte système — parsable côté frontend.
- La recommandation de négociation est cohérente avec l'écart calculé (-7 %).

**Trade-offs :**
| Critère | V1 | V2 | V3 |
|---|---|---|---|
| Format garanti | ❌ | ✅ | ✅ |
| Données vérifiables | ❌ | ❌ | ✅ |
| Tokens (input) | ~80 | ~120 | ~350 |
| Latence (Haiku) | ~0,8 s | ~0,9 s | ~1,2 s |
| Fiabilité métier | Faible | Moyenne | **Haute** |

Le surcoût de ~270 tokens d'input est marginal face au gain de fiabilité.
Avec le prompt caching Anthropic (même system prompt), le coût des appels répétés
est réduit de ~90 % sur la partie système.

---

## Conclusion

**Version retenue en production : V3**

Raison principale : seule version où les affirmations chiffrées du LLM sont
auditables et reproductibles — condition sine qua non pour un outil d'aide à la
décision immobilière impliquant des budgets de 200–400 k€.

La séparation stricte entre **calcul quantitatif** (Python from scratch) et
**argumentation qualitative** (LLM) est le cœur de l'architecture NidBuyer V2.
