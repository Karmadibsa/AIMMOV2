# Journal des expérimentations — Prompt Engineering

Comparaison de **3 versions** du system prompt sur le **même bien de référence**.

---

## Bien de référence

> **T3, 68m², Mourillon, 215 000€**
> Description : "Bel appartement lumineux, cuisine rénovée, balcon vue mer partielle, proximité plage du Mourillon."
> DVF quartier Mourillon : médiane 3 400 €/m² → bien à 3 162 €/m², soit **-7%**
> Profil testé : Investisseur locatif (INV), budget 250 000€

---

## V1 — Prompt basique

**system.txt**

```
Tu es NidBuyer, un conseiller immobilier IA spécialisé sur le marché de Toulon.

Tu aides les acheteurs à prendre des décisions d'achat éclairées en t'appuyant sur :
- Les vraies annonces du marché toulonnais
- Les données DVF (transactions réelles 2024-2026) par quartier
- Le profil et les objectifs de l'acheteur

Tu connais exactement 4 profils acheteurs et tu adaptes ton analyse en conséquence :
- RP (Résidence principale) : priorité au calme, confort familial proximité écoles
- INV (Investissement) : priorité au rendement locatif, quartier attractif à la location — les travaux sont une opportunité de négociation
- RS (Résidence secondaire) : priorité à la vue mer, proximité plage
- MIX (Immeuble mixte) : l'acheteur habite une partie et loue le reste — équilibre entre confort personnel et rendement

Tu es factuel, concis, et tu justifies toujours tes recommandations par des données chiffrées.
Tu ne spécules pas sur l'avenir du marché. Tu ne donnes pas de conseil juridique ou fiscal.
```

**fiche_decision.txt**

```
Voici les informations sur le bien immobilier :

{fiche_structuree}

Annonce originale :
{description_annonce}

Profil de l'acheteur : {profil}

Génère une analyse structurée avec exactement ces 4 sections :
1. **Opportunité** : le prix est-il attractif par rapport au marché du quartier ?
2. **Points forts** : les 2-3 atouts principaux pour ce profil
3. **Points d'attention** : les 1-2 risques ou limites à considérer
4. **Recommandation** : achat, négociation (fourchette), ou à éviter — et pourquoi

Sois direct et factuel. Utilise les données chiffrées fournies.
```

**Réponse obtenue sur le bien de référence :**

> **1. Opportunité**
> L'opportunité est réelle. Le prix au m² (3 162 €) affiche une décote de 7 % par rapport à la médiane du quartier Mourillon (3 400 €/m²). Cette sous-évaluation par rapport au marché local constitue un levier immédiat pour un investisseur.
>
> **2. Points forts**
>
> - **Emplacement à haute demande** : La proximité de la plage du Mourillon garantit une vacance locative minimale et une attractivité constante pour la location saisonnière ou longue durée.
> - **Valorisation locative** : La cuisine déjà rénovée et la présence d'un balcon avec vue mer partielle sont des caractéristiques qui permettent de viser le haut de la fourchette des loyers du secteur.
>
> **3. Points d'attention**
>
> - **Limitation de la vue** : La vue mer étant "partielle", le bien ne pourra pas prétendre aux loyers premium des biens avec vue panoramique totale.
> - **État de l'immeuble** : L'annonce met en avant la cuisine, mais il est crucial de vérifier l'état général des parties communes et les derniers appels de fonds de copropriété.
>
> **4. Recommandation**
> **Négociation (fourchette : 205 000 € - 210 000 €).**
> Bien que le prix soit déjà attractif (-7 %), une négociation permettrait d'optimiser le rendement locatif initial et de compenser d'éventuels travaux de rafraîchissement mineurs.

**Analyse :**

- Ce qui fonctionne : structuré, factuel, fourchette en euros présente
- Ce qui manque : format libre (l'IA choisit sa mise en forme), pas de raisonnement visible, difficile à intégrer de manière fiable dans une interface

---

## V2 — Format de sortie structuré

**system.txt** _(identique à V1)_

**fiche_decision_v2.txt**

```
Voici les informations sur le bien immobilier :

{fiche_structuree}

Annonce originale :
{description_annonce}

Profil de l'acheteur : {profil}

Réponds UNIQUEMENT dans ce format Markdown, sans introduction ni conclusion :

## 🏠 Opportunité
**Prix/m²** : X €/m² vs médiane quartier Y €/m² → écart : Z%
**Verdict** : Sous-évalué / Dans la norme / Surévalué

## ✅ Points forts
- Point 1 (avec chiffre)
- Point 2 (avec chiffre)

## ⚠️ Points d'attention
- Point 1
- Point 2

## 💡 Recommandation
**Action** : Acheter / Négocier / Éviter
**Fourchette de négociation** : entre Xa€ et Xb€
**Justification** : 2 phrases max, chiffrées
```

**Réponse obtenue sur le bien de référence :**

> ## 🏠 Opportunité
>
> **Prix/m²** : 3 162 €/m² vs médiane quartier 3 400 €/m² → écart : -7%
> **Verdict** : Sous-évalué
>
> ## ✅ Points forts
>
> - Localisation Mourillon à très forte demande locative
> - Prix d'acquisition déjà inférieur de 7% à la médiane du quartier
>
> ## ⚠️ Points d'attention
>
> - Vue mer "partielle" (limite le plafond de loyer par rapport à une vue totale)
> - Cuisine déjà rénovée (réduit le levier de négociation classique par les travaux)
>
> ## 💡 Recommandation
>
> **Action** : Négocier
> **Fourchette de négociation** : entre 204 000€ et 209 000€
> **Justification** : L'objectif est de descendre sous la barre des 3 050 €/m² pour maximiser le rendement brut. La cuisine étant déjà rénovée, la négociation doit porter sur l'absence d'autres travaux visibles ou sur l'écart de prix constaté.

**Analyse :**

- Ce qui s'est amélioré : format strictement respecté, facile à intégrer dans l'interface, verdict clair, fourchette précise
- Ce qui reste perfectible : l'IA donne des conclusions sans montrer son raisonnement — on ne sait pas pourquoi elle arrive à ces chiffres. L'acheteur reçoit des conclusions sans comprendre le "pourquoi".

---

## V3 — Chain-of-thought + intro narrative (2 itérations)

**system.txt** _(identique à V1)_

**fiche_decision_v3.txt**

```
Voici les informations sur le bien immobilier :

{fiche_structuree}

Annonce originale :
{description_annonce}

Profil de l'acheteur : {profil}

Raisonne en interne sur ces 4 axes avant de répondre :
1. PRIX : L'écart au DVF est-il significatif ? Calcule la valeur médiane en € (surface × médiane/m²)
2. PROFIL : Les critères prioritaires de ce profil sont-ils satisfaits ?
3. RISQUES : Quels éléments de l'annonce peuvent cacher un problème ?
4. NÉGOCIATION : Quel prix plancher est défendable avec les données DVF ?

Puis réponds dans ce format exact :

[Un paragraphe d'introduction de 2-3 phrases en langage naturel,
sans titre ni bullet points, qui mentionne obligatoirement :
- le prix/m² et l'écart à la médiane en % ET en €
- ce que ça implique concrètement pour le profil de l'acheteur]

## 🏠 Opportunité
**Prix/m²** : X €/m² vs médiane quartier Y €/m² → écart : Z%
**Verdict** : Sous-évalué / Dans la norme / Surévalué

## ✅ Points forts
- Point 1 (avec chiffre)
- Point 2 (avec chiffre)

## ⚠️ Points d'attention
- Point 1
- Point 2

## 💡 Recommandation
**Action** : Acheter / Négocier / Éviter
**Fourchette de négociation** : entre Xa€ et Xb€
**Justification** : 2 phrases max, chiffrées
```

### Itération V3a — réflexion visible

Première tentative avec les balises `<reflexion>` affichées dans la réponse. La chaîne de raisonnement apparaissait telle quelle, ce qui n'est pas adapté à une interface utilisateur.

> La réflexion était visible mais encombrante — le raisonnement était bon mais la mise en forme inappropriée pour l'affichage final.

### Itération V3b — intro narrative (version finale)

Raisonnement internalisé, réécrit sous forme d'un paragraphe d'introduction en langage naturel pour l'acheteur.

**Réponse obtenue sur le bien de référence :**

> Ce bien s'affiche à 3 162 €/m², soit une décote de 7% (-16 200 €) par rapport à la médiane du quartier. Pour un profil investisseur, cette différence de prix constitue un levier immédiat pour optimiser le rendement locatif et sécuriser la rentabilité de l'opération.
>
> ## 🏠 Opportunité
>
> **Prix/m²** : 3 162 €/m² vs médiane quartier 3 400 €/m² → écart : -7%
> **Verdict** : Sous-évalué
>
> ## ✅ Points forts
>
> - Économie immédiate de 16 200 € par rapport à la valeur médiane du secteur
> - Emplacement à haute tension locative (proximité plage du Mourillon)
>
> ## ⚠️ Points d'attention
>
> - État de l'appartement hors cuisine (vérifier le besoin de travaux pour maintenir le rendement)
> - Vue mer "partielle" qui peut limiter la prime de loyer par rapport à une vue totale
>
> ## 💡 Recommandation
>
> **Action** : Négocier
> **Fourchette de négociation** : entre 205 000 € et 210 000 €
> **Justification** : Viser 208 000 € permettrait de porter la décote à environ 10% de la médiane. Cela offre une marge de sécurité financière pour d'éventuels travaux de mise aux normes.

**Analyse :**

- Pourquoi V3 > V1 : le raisonnement interne force le modèle à contextualiser l'écart en euros (-16 200€) et non juste en pourcentage (-7%),ce qui rend l'analyse plus concrète pour l'acheteur.
- Pourquoi V3 > V2 : même format structuré, mais l'intro narrative explique le raisonnement à l'acheteur en langage naturel — il comprend _pourquoi_ c'est une opportunité avant de lire les conclusions.
- Trade-off : réponse légèrement plus longue (+20% de tokens vs V2), latence marginalement supérieure — largement justifié pour une décision d'achat immobilier.

---

## Conclusion

Version retenue en production : **V3b**

Raison principale : la chain-of-thought interne force le modèle à raisonner sur 4 axes (prix, profil, risques, négociation) avant de répondre, ce qui produit des justifications chiffrées et traçables. L'intro narrative en langage naturel rend l'analyse accessible à l'acheteur sans jargon technique. Le système prompt enrichi avec les 4 profils (RP, INV, RS, MIX) garantit une analyse automatiquement adaptée au contexte de chaque acheteur. Ce format combine la rigueur analytique de la V3 et la lisibilité de la V2.
