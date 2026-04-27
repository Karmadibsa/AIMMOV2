# Journal des expérimentations — Prompt Engineering

Comparaison de **3 versions** du system prompt sur le **même bien de référence**.

---

## Bien de référence

> **T3, 68m², Mourillon, 215 000€**
> Description : "Bel appartement lumineux, cuisine rénovée, balcon vue mer partielle, proximité plage du Mourillon."
> DVF quartier Mourillon : médiane 3 400 €/m² → bien à 3 162 €/m², soit **-7%**
> Profil testé : Investisseur, budget 250 000€

---

## V1 — Prompt basique

**system.txt**
```
Tu es NidBuyer, un conseiller immobilier IA spécialisé sur le marché de Toulon.

Tu aides les acheteurs à prendre des décisions d'achat éclairées en t'appuyant sur :
- Les vraies annonces du marché toulonnais
- Les données DVF (transactions réelles 2024-2026) par quartier
- Le profil et les objectifs de l'acheteur

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
> Le bien est affiché à 3 162€/m², soit 7% sous la médiane DVF du Mourillon (3 400€/m²). C'est un prix attractif.
>
> **2. Points forts**
> - Prix sous le marché, marge de négociation possible
> - Cuisine rénovée, moins de travaux immédiats
> - Localisation Mourillon, quartier recherché à Toulon
>
> **3. Points d'attention**
> - "Vue mer partielle" peut limiter la valorisation locative
> - Rendement locatif non calculable sans données de loyers du secteur
>
> **4. Recommandation**
> Achat ou négociation. Le prix sous la médiane offre une marge de 3-5%. Budget compatible (215k < 250k).

**Analyse :**
- Ce qui fonctionne : structuré, factuel, concis
- Ce qui manque : pas de raisonnement visible, conseil trop générique, pas assez adapté au profil investisseur, pas de fourchette de négociation en euros

---

## V2 — Format de sortie structuré

**fiche_decision.txt** *(system.txt identique à V1)*
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

## ✅ Points forts pour ce profil
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
> **Prix/m²** : 3 162 €/m² vs médiane quartier 3 400 €/m² → écart : -7%
> **Verdict** : Sous-évalué
>
> ## ✅ Points forts pour ce profil (Investisseur)
> - Prix 7% sous la médiane = marge de négociation immédiate de 3-5%
> - Cuisine rénovée = pas de travaux à prévoir, mise en location rapide
>
> ## ⚠️ Points d'attention
> - Vue mer "partielle" → loyer plafonné, moins attractif qu'un bien vue mer totale
> - Pas de données de loyers disponibles pour calculer le rendement brut
>
> ## 💡 Recommandation
> **Action** : Négocier
> **Fourchette de négociation** : entre 204 000€ et 208 000€
> **Justification** : Le bien est déjà sous la médiane DVF. Une offre à -5% reste justifiable par les données du marché et l'absence de vue mer franche.

**Analyse :**
- Ce qui s'est amélioré : format lisible, chiffres précis, fourchette de négociation en euros, verdict clair
- Ce qui reste perfectible : l'IA donne des conclusions sans montrer son raisonnement

---

## V3 — Chain-of-thought

**fiche_decision.txt** *(system.txt identique à V1)*
```
Voici les informations sur le bien immobilier :

{fiche_structuree}

Annonce originale :
{description_annonce}

Profil de l'acheteur : {profil}

Avant de répondre, raisonne étape par étape en suivant exactement cette séquence :

<reflexion>
1. PRIX : Compare le prix/m² au DVF du quartier. L'écart est-il significatif ? Pourquoi ?
2. PROFIL : Quels sont les critères prioritaires de cet acheteur ? Ce bien y répond-il ?
3. RISQUES : Quels éléments de l'annonce ou du marché peuvent poser problème ?
4. NÉGOCIATION : Quel est le prix plancher raisonnable basé sur les données DVF ?
</reflexion>

Puis réponds UNIQUEMENT dans ce format :

## 🏠 Opportunité
**Prix/m²** : X €/m² vs médiane quartier Y €/m² → écart : Z%
**Verdict** : Sous-évalué / Dans la norme / Surévalué

## ✅ Points forts pour ce profil
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

> <reflexion>
> 1. **PRIX** : Le bien est à 3 162€/m² vs médiane DVF Mourillon à 3 400€/m². Écart de -7%, soit 238€/m² sous le marché. Sur 68m², ça représente 16 184€ de moins que la valeur médiane. C'est significatif et objectivement justifiable auprès du vendeur.
>
> 2. **PROFIL** : Investisseur, budget 250k. Critères prioritaires : rendement locatif, faible besoin de travaux, quartier attractif pour la location. La cuisine rénovée coche la case "pas de travaux immédiats". Le Mourillon est le quartier le plus recherché de Toulon à la location.
>
> 3. **RISQUES** : "Vue mer partielle" est un argument marketing flou — à vérifier sur place. Sans données de loyers du secteur, le rendement brut est incalculable précisément. Risque de surestimer l'attractivité locative.
>
> 4. **NÉGOCIATION** : Médiane DVF à 3 400€/m². Le bien est déjà à -7%. Une offre à -5% supplémentaire soit 204 000€ reste défendable. Plancher absolu : 200 000€ (-7% sur le prix affiché).
> </reflexion>
>
> ## 🏠 Opportunité
> **Prix/m²** : 3 162 €/m² vs médiane quartier 3 400 €/m² → écart : -7%
> **Verdict** : Sous-évalué
>
> ## ✅ Points forts pour ce profil (Investisseur)
> - Bien déjà 16 184€ sous la valeur médiane DVF → levier de négociation immédiat
> - Cuisine rénovée → mise en location possible sans travaux, rendement dès l'achat
>
> ## ⚠️ Points d'attention
> - "Vue mer partielle" à vérifier sur place — impact direct sur le loyer potentiel
> - Rendement brut non calculable sans données de loyers Mourillon
>
> ## 💡 Recommandation
> **Action** : Négocier
> **Fourchette de négociation** : entre 200 000€ et 204 000€
> **Justification** : Le bien est déjà sous la médiane DVF. La cuisine rénovée limite les travaux mais l'absence de vraie vue mer justifie une pression supplémentaire de 3-5% sur le prix affiché.

**Analyse :**
- Pourquoi V3 > V1 : le raisonnement est visible et traçable, les chiffres sont contextualisés (16 184€ sous la médiane vs juste "-7%"), les risques sont nuancés
- Trade-off : réponse plus longue (+30%), coût en tokens plus élevé, latence légèrement supérieure — justifié pour une décision d'achat immobilier

---

## Conclusion

Version retenue en production : **V3**

Raison principale : la chain-of-thought produit des analyses plus précises et mieux adaptées au profil acheteur, ce qui est critique pour une décision d'achat immobilier. Le surcoût en tokens est acceptable au vu de la qualité du conseil.