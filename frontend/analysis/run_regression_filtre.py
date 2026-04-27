"""
Script de démonstration de la régression linéaire from scratch.
Entraîne 2 modèles : un pour les appartements, un pour les maisons.
"""

import pandas as pd
import math
from analysis.stats import mean, correlation
from analysis.regression import predict, sum_of_sqerrors, least_squares_fit, r_squared

# ═══════════════════════════════════════════════════════════════
# FONCTION HELPER : Analyser un type de bien
# ═══════════════════════════════════════════════════════════════

def analyser_type_bien(df, type_bien, prix_m2_min, prix_m2_max):
    """
    Analyse un type de bien (Appartement ou Maison).
    
    Args:
        df: DataFrame pandas avec toutes les données
        type_bien: "Appartement" ou "Maison"
        prix_m2_min: Prix/m² minimum pour filtrage
        prix_m2_max: Prix/m² maximum pour filtrage
    
    Returns:
        dict avec alpha, beta, r2, opportunites, stats
    """
    print("\n" + "=" * 70)
    print(f"RÉGRESSION {type_bien.upper()}S")
    print("=" * 70)
    
    # Filtrer par type
    df_type = df[df['type_local'] == type_bien].copy()
    print(f"\n📊 {len(df_type)} {type_bien.lower()}s dans les données")
    
    if len(df_type) < 50:
        print(f"   ⚠️  Pas assez de données pour une régression fiable (minimum 50)")
        return None
    
    # Calculer prix/m²
    df_type['prix_m2'] = df_type['valeur_fonciere'] / df_type['surface_reelle_bati']
    
    # Filtrage prix/m²
    print(f"\n💰 Filtrage par prix/m² ({prix_m2_min}-{prix_m2_max}€/m²)...")
    print(f"   Avant : {len(df_type)} {type_bien.lower()}s")
    
    df_type = df_type[(df_type['prix_m2'] >= prix_m2_min) & (df_type['prix_m2'] <= prix_m2_max)]
    
    print(f"   Après : {len(df_type)} {type_bien.lower()}s conservés")
    
    if len(df_type) < 30:
        print(f"   ⚠️  Trop peu de données après filtrage")
        return None
    
    # Conversion en listes
    surfaces = df_type['surface_reelle_bati'].tolist()
    prix = df_type['valeur_fonciere'].tolist()
    
    # Nettoyage NaN (normalement déjà fait, mais sécurité)
    surfaces_clean = []
    prix_clean = []
    for s, p in zip(surfaces, prix):
        if not math.isnan(s) and not math.isnan(p) and s > 0:
            surfaces_clean.append(s)
            prix_clean.append(p)
    
    surfaces = surfaces_clean
    prix = prix_clean
    
    # Corrélation
    corr = correlation(surfaces, prix)
    print(f"\n📈 Corrélation prix/surface : {corr:.4f}")
    
    # Régression
    print(f"\n🤖 Entraînement du modèle...")
    alpha, beta = least_squares_fit(surfaces, prix)
    
    print(f"\n📊 MODÈLE TROUVÉ")
    print(f"   Prix_{type_bien.lower()} = {alpha:,.0f} + {beta:,.0f} × Surface".replace(',', ' '))
    print(f"   • alpha (prix de base) : {alpha:,.0f} €".replace(',', ' '))
    print(f"   • beta (prix par m²)   : {beta:,.0f} €/m²".replace(',', ' '))
    
    # R²
    r2 = r_squared(alpha, beta, surfaces, prix)
    print(f"\n📈 Qualité du modèle : R² = {r2:.4f} ({r2*100:.1f}%)")
    
    if r2 >= 0.60:
        print(f"   ✅ BON - Le modèle explique {r2*100:.1f}% de la variation")
    elif r2 >= 0.40:
        print(f"   ⚠️  MOYEN - Acceptable pour un MVP")
    else:
        print(f"   ❌ FAIBLE - Le quartier domine probablement")
    
    # Opportunités
    opportunites = []
    for surf, prix_reel in zip(surfaces, prix):
        prix_predit = predict(alpha, beta, surf)
        ecart_pct = ((prix_reel - prix_predit) / prix_predit) * 100
        
        if ecart_pct < -8 and prix_reel <= 450000:
            opportunites.append({
                'type': type_bien,
                'surface': surf,
                'prix_reel': prix_reel,
                'prix_predit': prix_predit,
                'ecart_pct': ecart_pct,
                'economie': prix_predit - prix_reel
            })
    
    opportunites.sort(key=lambda x: x['economie'], reverse=True)
    
    print(f"\n🎯 OPPORTUNITÉS ({type_bien.lower()}s)")
    print(f"   • {len(opportunites)} {type_bien.lower()}s sous-évalués identifiés")
    print(f"   • TOP 5 :")
    
    for i, opp in enumerate(opportunites[:5], start=1):
        print(f"      #{i} | {opp['surface']:.0f}m² | {opp['prix_reel']:,.0f}€ | {opp['ecart_pct']:.1f}% | 💰 {opp['economie']:,.0f}€".replace(',', ' '))
    
    # Retourner les résultats
    return {
        'type': type_bien,
        'alpha': alpha,
        'beta': beta,
        'r2': r2,
        'correlation': corr,
        'nb_biens': len(surfaces),
        'opportunites': opportunites,
        'surfaces': surfaces,
        'prix': prix
    }


# ═══════════════════════════════════════════════════════════════
# MAIN : CHARGEMENT ET ANALYSE
# ═══════════════════════════════════════════════════════════════

print("=" * 70)
print("OBSERVATOIRE IMMOBILIER TOULONNAIS - RÉGRESSION FROM SCRATCH")
print("=" * 70)

# Chargement
print("\n📁 Chargement des données...")
df = pd.read_csv("data/dvf_toulon.csv")
print(f"   ✅ {len(df)} transactions chargées")

# Répartition
print("\n📊 Répartition des types de biens :")
print(f"   • Appartements : {len(df[df['type_local'] == 'Appartement'])}")
print(f"   • Maisons      : {len(df[df['type_local'] == 'Maison'])}")

# Analyse APPARTEMENTS
resultats_apparts = analyser_type_bien(
    df, 
    type_bien="Appartement",
    prix_m2_min=3500,
    prix_m2_max=10000
)

# Analyse MAISONS
resultats_maisons = analyser_type_bien(
    df,
    type_bien="Maison",
    prix_m2_min=2000,
    prix_m2_max=6000
)

# ═══════════════════════════════════════════════════════════════
# SYNTHÈSE FINALE
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("📊 SYNTHÈSE GÉNÉRALE")
print("=" * 70)

# Modèles
print("\n🤖 MODÈLES TROUVÉS :")
if resultats_apparts:
    print(f"\n   Appartements :")
    print(f"      Prix = {resultats_apparts['alpha']:,.0f} + {resultats_apparts['beta']:,.0f} × Surface".replace(',', ' '))
    print(f"      R² = {resultats_apparts['r2']:.2%} | Corrélation = {resultats_apparts['correlation']:.3f}")

if resultats_maisons:
    print(f"\n   Maisons :")
    print(f"      Prix = {resultats_maisons['alpha']:,.0f} + {resultats_maisons['beta']:,.0f} × Surface".replace(',', ' '))
    print(f"      R² = {resultats_maisons['r2']:.2%} | Corrélation = {resultats_maisons['correlation']:.3f}")

# Opportunités totales
print("\n🎯 OPPORTUNITÉS GLOBALES :")

toutes_opportunites = []
if resultats_apparts:
    toutes_opportunites.extend(resultats_apparts['opportunites'])
if resultats_maisons:
    toutes_opportunites.extend(resultats_maisons['opportunites'])

toutes_opportunites.sort(key=lambda x: x['economie'], reverse=True)

print(f"\n   ✅ {len(toutes_opportunites)} opportunités identifiées au total")
print(f"\n   🏆 TOP 10 TOUTES CATÉGORIES :")
print()

for i, opp in enumerate(toutes_opportunites[:10], start=1):
    type_emoji = "🏢" if opp['type'] == "Appartement" else "🏠"
    print(f"   #{i:02d} {type_emoji} {opp['type']:<12} | {opp['surface']:>5.0f}m² | {opp['prix_reel']:>10,.0f}€ | {opp['ecart_pct']:>6.1f}% | 💰 {opp['economie']:>10,.0f}€".replace(',', ' '))

# Statistiques opportunités
if len(toutes_opportunites) > 0:
    economie_moyenne = sum(o['economie'] for o in toutes_opportunites) / len(toutes_opportunites)
    economie_totale = sum(o['economie'] for o in toutes_opportunites)
    
    print(f"\n   📊 Statistiques :")
    print(f"      • Économie moyenne : {economie_moyenne:,.0f}€".replace(',', ' '))
    print(f"      • Économie totale potentielle : {economie_totale:,.0f}€".replace(',', ' '))
    
    nb_apparts_opp = len([o for o in toutes_opportunites if o['type'] == 'Appartement'])
    nb_maisons_opp = len([o for o in toutes_opportunites if o['type'] == 'Maison'])
    print(f"      • Appartements : {nb_apparts_opp} opportunités")
    print(f"      • Maisons      : {nb_maisons_opp} opportunités")

print("\n" + "=" * 70)
print("✅ Analyse terminée !")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════
# EXPORT POUR LE FRONTEND
# ═══════════════════════════════════════════════════════════════

# import json

# modeles = {
#     'appartements': {
#         'alpha': resultats_apparts['alpha'] if resultats_apparts else None,
#         'beta': resultats_apparts['beta'] if resultats_apparts else None,
#         'r2': resultats_apparts['r2'] if resultats_apparts else None,
#     } if resultats_apparts else None,
#     'maisons': {
#         'alpha': resultats_maisons['alpha'] if resultats_maisons else None,
#         'beta': resultats_maisons['beta'] if resultats_maisons else None,
#         'r2': resultats_maisons['r2'] if resultats_maisons else None,
#     } if resultats_maisons else None,
#     'opportunites': toutes_opportunites[:20]  # Top 20 pour le frontend
# }

# # Sauvegarder en JSON
# with open('donnees/modeles_regression.json', 'w', encoding='utf-8') as f:
#     json.dump(modeles, f, indent=2, ensure_ascii=False)

# print("\n💾 Modèles sauvegardés dans donnees/modeles_regression.json")