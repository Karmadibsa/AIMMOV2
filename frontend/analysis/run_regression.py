"""
Script de démonstration de la régression linéaire from scratch.
Entraîne un modèle Prix = alpha + beta × Surface sur les données DVF.
"""

import pandas as pd
import math
from analysis.stats import mean
from analysis.regression import predict, sum_of_sqerrors, least_squares_fit, r_squared

# # ═══════════════════════════════════════════════════════════════
# # 1. CHARGEMENT DES DONNÉES
# # ═══════════════════════════════════════════════════════════════

# print("=" * 70)
# print("RÉGRESSION LINÉAIRE : Prix = alpha + beta × Surface")
# print("=" * 70)
# print("\n📁 Chargement des données...")

# df = pd.read_csv("donnees/dvf-nettoyer_800_day.csv")

# # Conversion en listes Python
# prix_bruts = df['valeur_fonciere'].tolist()
# surfaces_brutes = df['surface_reelle_bati'].tolist()

# print(f"   ✅ {len(prix_bruts)} transactions chargées")

# ═══════════════════════════════════════════════════════════════
# 1. CHARGEMENT DES DONNÉES
# ═══════════════════════════════════════════════════════════════

print("=" * 70)
print("RÉGRESSION LINÉAIRE : Prix = alpha + beta × Surface")
print("=" * 70)
print("\n📁 Chargement des données...")

df = pd.read_csv("data/dvf_toulon.csv")

print(f"   ✅ {len(df)} transactions chargées")

# ═══════════════════════════════════════════════════════════════
# 1.5 FILTRAGE PAR TYPE
# ═══════════════════════════════════════════════════════════════

print("\n🏠 Filtrage par type de bien...")

print(f"   Répartition avant filtrage :")
print(f"      • Appartements : {len(df[df['type_local'] == 'Appartement'])}")
print(f"      • Maisons      : {len(df[df['type_local'] == 'Maison'])}")

# GARDER SEULEMENT LES APPARTEMENTS
df = df[df['type_local'] == 'Appartement']

print(f"\n   ✅ {len(df)} appartements conservés pour l'analyse")
print(f"   ℹ️  Focus : Primo-accédants (typiquement acheteurs d'appartements)")

# ═══════════════════════════════════════════════════════════════
# 1.6 FILTRAGE PAR PRIX/M²
# ═══════════════════════════════════════════════════════════════

print("\n💰 Filtrage par prix/m²...")

# Calculer prix/m²
df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']

print(f"   Avant : {len(df)} appartements")

# Garder seulement prix/m² raisonnables (ni trop bas, ni trop haut)
df = df[(df['prix_m2'] >= 3500) & (df['prix_m2'] <= 10000)]

print(f"   Après : {len(df)} appartements (filtrés 3500-10000€/m²)")

# Conversion en listes Python
prix_bruts = df['valeur_fonciere'].tolist()
surfaces_brutes = df['surface_reelle_bati'].tolist()

# Conversion en listes Python
prix_bruts = df['valeur_fonciere'].tolist()
surfaces_brutes = df['surface_reelle_bati'].tolist()

# ═══════════════════════════════════════════════════════════════
# 2. NETTOYAGE DES DONNÉES
# ═══════════════════════════════════════════════════════════════

print("\n🧹 Nettoyage des données (suppression des NaN)...")

prix = []
surfaces = []

for p, s in zip(prix_bruts, surfaces_brutes):
    # On garde seulement les lignes où prix ET surface sont valides
    if not math.isnan(p) and not math.isnan(s) and s > 0:
        prix.append(p)
        surfaces.append(s)

print(f"   ✅ {len(prix)} transactions valides conservées")
print(f"   ❌ {len(prix_bruts) - len(prix)} transactions supprimées (données manquantes)")

# ═══════════════════════════════════════════════════════════════
# 3. ENTRAÎNEMENT DU MODÈLE
# ═══════════════════════════════════════════════════════════════

print("\n🤖 Entraînement du modèle de régression...")

alpha, beta = least_squares_fit(surfaces, prix)

print(f"\n📊 MODÈLE TROUVÉ")
print("=" * 70)
print(f"   Prix = {alpha:,.2f} + {beta:,.2f} × Surface".replace(',', ' '))
print()
print(f"   📌 alpha (ordonnée à l'origine) : {alpha:,.2f} €".replace(',', ' '))
print(f"   📌 beta (prix par m²)            : {beta:,.2f} €/m²".replace(',', ' '))

# ═══════════════════════════════════════════════════════════════
# 4. ÉVALUATION DE LA QUALITÉ DU MODÈLE
# ═══════════════════════════════════════════════════════════════

print("\n📈 Évaluation de la qualité du modèle...")

r2 = r_squared(alpha, beta, surfaces, prix)

print(f"\n   R² = {r2:.4f} ({r2*100:.2f}%)".replace(',', ' '))

# Interprétation automatique
if r2 >= 0.90:
    qualite = "✅ EXCELLENT"
    interpretation = f"Le modèle explique {r2*100:.1f}% de la variation des prix."
elif r2 >= 0.70:
    qualite = "✅ BON"
    interpretation = f"Le modèle explique {r2*100:.1f}% de la variation des prix."
elif r2 >= 0.50:
    qualite = "⚠️  MOYEN"
    interpretation = f"Le modèle explique seulement {r2*100:.1f}% de la variation."
else:
    qualite = "❌ FAIBLE"
    interpretation = f"Le modèle n'explique que {r2*100:.1f}% de la variation."

print(f"   {qualite}")
print(f"   {interpretation}")

print("\n📊 Régression par section cadastrale (proxy quartier) :")
print("-" * 100)
print(f"{'Section':10s} {'Quartier':25s} {'n':>5s} {'R²':>6s} {'Prix moy':>12s} {'Surf moy':>9s} {'Prix/m²':>9s} {'Modèle'}")
print("-" * 100)

# Mapping sections → noms de quartiers (à adapter selon votre connaissance du terrain)
QUARTIERS = {
    "000BV": "Mourillon",
    "000BX": "Mourillon Est",
    "000BY": "Mourillon Centre",
    "000CL": "Centre-Ville",
    "000BT": "Port Marchand",
    "000CM": "Haute-Ville",
    # Ajoutez d'autres correspondances...
}
col_quartier = "section_prefixe"

quartiers = df[col_quartier].unique()
for q in sorted(quartiers):
    sub = df[df[col_quartier] == q]
    if len(sub) < 10:
        continue
    
    surfaces = sub["surface_reelle_bati"].tolist()
    prix = sub["valeur_fonciere"].tolist()
    
    # Statistiques descriptives
    prix_moyen = int(sum(prix) / len(prix))
    surf_moyenne = int(sum(surfaces) / len(surfaces))
    prix_m2_moyen = int(prix_moyen / surf_moyenne) if surf_moyenne > 0 else 0
    
    # Régression
    alpha_q, beta_q = least_squares_fit(surfaces, prix)
    r2_q = r_squared(alpha_q, beta_q, surfaces, prix)
    
    # Nom du quartier
    nom_quartier = QUARTIERS.get(q, "Section " + q)
    
    # Qualité du modèle
    if r2_q >= 0.8:
        qualite = "✅"
    elif r2_q >= 0.6:
        qualite = "⚠️"
    else:
        qualite = "❌"
    
    print(f"{q:10s} {nom_quartier:25s} {len(sub):5d} {r2_q:6.2f} {prix_moyen:12,d}€ {surf_moyenne:9.1f}m² {prix_m2_moyen:9,d}€ {qualite}")

print("\n💡 Interprétation pour agents immobiliers :")
print("   ✅ R² ≥ 0.80 : Modèle fiable — la surface explique bien le prix")
print("   ⚠️  R² 0.60-0.80 : Modèle correct — autres facteurs importants (standing, vue)")
print("   ❌ R² < 0.60 : Modèle faible — forte hétérogénéité du quartier")

# Détails du calcul
ss_res = sum_of_sqerrors(alpha, beta, surfaces, prix)
mean_prix = mean(prix)
ss_tot = sum((p - mean_prix) ** 2 for p in prix)

print(f"\n   📊 Détails du calcul :")
print(f"      SS_res (erreur du modèle)     : {ss_res:,.0f}".replace(',', ' '))
print(f"      SS_tot (erreur de la moyenne) : {ss_tot:,.0f}".replace(',', ' '))

# ═══════════════════════════════════════════════════════════════
# 5. PRÉDICTIONS POUR DIFFÉRENTES SURFACES
# ═══════════════════════════════════════════════════════════════

print("\n🔮 PRÉDICTIONS pour différentes surfaces")
print("=" * 70)

# Surfaces typiques pour des primo-accédants
surfaces_test = [40, 50, 60, 70, 80, 90, 100]

for surf in surfaces_test:
    prix_predit = predict(alpha, beta, surf)
    dans_budget = "✅" if prix_predit <= 450000 else "❌"
    print(f"   {surf}m² → {prix_predit:>10,.2f} € {dans_budget}".replace(',', ' '))

print("\n   ✅ = Dans le budget primo-accédants (≤ 450 000 €)")
print("   ❌ = Hors budget")

# ═══════════════════════════════════════════════════════════════
# 6. IDENTIFICATION DES OPPORTUNITÉS
# ═══════════════════════════════════════════════════════════════

print("\n🎯 IDENTIFICATION DES OPPORTUNITÉS (biens sous-évalués)")
print("=" * 70)

# Pour chaque bien, calculer l'écart avec le prix prédit
opportunites = []

for surf, prix_reel in zip(surfaces, prix):
    prix_predit = predict(alpha, beta, surf)
    ecart_euros = prix_reel - prix_predit
    ecart_pct = (ecart_euros / prix_predit) * 100
    
    # On considère comme opportunité si le bien est au moins 8% sous le prix prédit
    # ET dans le budget primo-accédants
    if ecart_pct < -8 and prix_reel <= 450000:
        opportunites.append({
            'surface': surf,
            'prix_reel': prix_reel,
            'prix_predit': prix_predit,
            'ecart_pct': ecart_pct,
            'economie': prix_predit - prix_reel
        })

# Trier par économie décroissante (meilleures opportunités en premier)
opportunites.sort(key=lambda x: x['economie'], reverse=True)

# Afficher le TOP 10
print(f"\n   🏆 TOP 10 des meilleures opportunités :")
print()

if len(opportunites) > 0:
    for i, opp in enumerate(opportunites[:10], start=1):
        print(f"   #{i:02d} | {opp['surface']:>5.0f}m² | {opp['prix_reel']:>10,.0f} € | Écart: {opp['ecart_pct']:>6.1f}% | Économie: {opp['economie']:>10,.0f} €".replace(',', ' '))
else:
    print("   ⚠️  Aucune opportunité trouvée avec les critères actuels.")

print(f"\n   📊 Statistiques :")
print(f"      • {len(opportunites)} opportunités identifiées (écart < -8% et ≤ 450k€)")
print(f"      • {len([o for o in opportunites if o['ecart_pct'] < -15])} opportunités majeures (écart < -15%)")

if len(opportunites) > 0:
    economie_moyenne = sum(o['economie'] for o in opportunites) / len(opportunites)
    print(f"      • Économie moyenne : {economie_moyenne:,.2f} €".replace(',', ' '))

# ═══════════════════════════════════════════════════════════════
# 7. STATISTIQUES GLOBALES
# ═══════════════════════════════════════════════════════════════

print("\n📊 STATISTIQUES GLOBALES")
print("=" * 70)

# Prix moyen réel vs prix moyen prédit
prix_moyen_reel = mean(prix)
prix_moyen_predit = mean([predict(alpha, beta, s) for s in surfaces])

print(f"   Prix moyen réel   : {prix_moyen_reel:>12,.2f} €".replace(',', ' '))
print(f"   Prix moyen prédit : {prix_moyen_predit:>12,.2f} €".replace(',', ' '))

# Surface moyenne
surface_moyenne = mean(surfaces)
print(f"\n   Surface moyenne   : {surface_moyenne:>12.2f} m²".replace(',', ' '))

# Taux d'opportunités
taux_opportunites = (len(opportunites) / len(prix)) * 100 if len(prix) > 0 else 0
print(f"\n   Taux d'opportunités : {taux_opportunites:.2f}% des biens")

print("\n" + "=" * 70)
print("✅ Analyse terminée !")
print("=" * 70)