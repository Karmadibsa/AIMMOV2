"""
Script de préparation des données de régression linéaire pour le front-end.
Entraîne 2 modèles : un pour les appartements, un pour les maisons, 
et génère un fichier JSON structuré.
"""

import pandas as pd
import math
import json
import os

# Assure-toi que ces modules existent bien dans ton projet
from analysis.stats import mean, correlation
from analysis.regression import predict, sum_of_sqerrors, least_squares_fit, r_squared

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

QUARTIERS = {
    "000AH": "Le Faron",
    "000AM": "Saint-Jean du Var",
    "000AN": "Saint-Jean du Var Sud",
    "000AP": "Rodeilhac",
    "000AR": "Les Routes",
    "000AS": "Les Routes Sud",
    "000AT": "Claret",
    "000AX": "Siblas",
    "000BD": "Cap Brun",
    "000BE": "Cap Brun Est",
    "000BH": "Pont du Las",
    "000BK": "Pont du Las Est",
    "000BN": "Le Jonquet",
    "000BO": "Le Jonquet Sud",
    "000BP": "La Loubière",
    "000BR": "Saint-Roch",
    "000BS": "Saint-Roch Sud",
    "000BT": "Port Marchand",
    "000BV": "Mourillon",
    "000BW": "Mourillon Ouest",
    "000BX": "Mourillon Est",
    "000BY": "Mourillon Centre",
    "000CH": "Le Cours Lafayette",
    "000CI": "Valbertrand",
    "000CK": "La Serinette",
    "000CL": "Centre-Ville",
    "000CM": "Haute-Ville",
    "000CN": "Besagne",
    "000CO": "Besagne Sud",
    "000CP": "La Rode",
    "000CW": "Brunet",
    "000CX": "Le Champ de Mars",
    "000CY": "Sainte-Musse",
    "000DI": "La Beaucaire",
    "000DK": "La Valette Frontière",
    "000DL": "Dardennes",
    "000DT": "Les Lices",
    "000DV": "Le Revest Frontière",
}

COL_QUARTIER = "section_prefixe"

# ═══════════════════════════════════════════════════════════════
# FONCTIONS D'ANALYSE
# ═══════════════════════════════════════════════════════════════

def analyser_type_bien(df, type_bien, prix_m2_min, prix_m2_max):
    """Calcule la régression linéaire globale et détecte les opportunités pour un type de bien."""
    print(f"🔄 Analyse des {type_bien.lower()}s en cours...")
    
    df_type = df[df['type_local'] == type_bien].copy()
    
    if len(df_type) < 50:
        print(f"⚠️ Pas assez de données pour {type_bien}")
        return None
    
    df_type['prix_m2'] = df_type['valeur_fonciere'] / df_type['surface_reelle_bati']
    df_type = df_type[(df_type['prix_m2'] >= prix_m2_min) & (df_type['prix_m2'] <= prix_m2_max)]
    
    surfaces = df_type['surface_reelle_bati'].tolist()
    prix = df_type['valeur_fonciere'].tolist()
    
    # Nettoyage NaN
    surfaces_clean, prix_clean = [], []
    for s, p in zip(surfaces, prix):
        if not math.isnan(s) and not math.isnan(p) and s > 0:
            surfaces_clean.append(float(s))
            prix_clean.append(float(p))
            
    if len(surfaces_clean) < 30:
        return None

    corr = correlation(surfaces_clean, prix_clean)
    alpha, beta = least_squares_fit(surfaces_clean, prix_clean)
    r2 = r_squared(alpha, beta, surfaces_clean, prix_clean)
    
    # Recherche d'opportunités (sous-évalués de plus de 8%)
    opportunites = []
    for surf, prix_reel in zip(surfaces_clean, prix_clean):
        prix_predit = predict(alpha, beta, surf)
        ecart_pct = ((prix_reel - prix_predit) / prix_predit) * 100
        
        if ecart_pct < -8 and prix_reel <= 450000:
            opportunites.append({
                'type': type_bien,
                'surface': float(surf),
                'prix_reel': float(prix_reel),
                'prix_predit': float(prix_predit),
                'ecart_pct': float(ecart_pct),
                'economie': float(prix_predit - prix_reel)
            })
            
    opportunites.sort(key=lambda x: x['economie'], reverse=True)
    
    return {
        'type': type_bien,
        'alpha': float(alpha),
        'beta': float(beta),
        'r2': float(r2),
        'correlation': float(corr),
        'nb_biens': len(surfaces_clean),
        'opportunites': opportunites
    }

def regression_par_quartier(df, type_bien):
    """Calcule la régression linéaire pour chaque quartier individuellement."""
    print(f"🔄 Calcul par quartiers pour les {type_bien.lower()}s...")
    df_filtre = df[df['type_local'] == type_bien]
    quartiers_presents = df_filtre[COL_QUARTIER].dropna().unique()
    
    resultats = []
    
    for q in sorted(quartiers_presents):
        sub = df_filtre[df_filtre[COL_QUARTIER] == q]
        if len(sub) < 10:
            continue
            
        surfaces = sub["surface_reelle_bati"].tolist()
        prix = sub["valeur_fonciere"].tolist()
        
        surfaces_clean, prix_clean = [], []
        for s, p in zip(surfaces, prix):
            if not math.isnan(s) and not math.isnan(p) and s > 0:
                surfaces_clean.append(float(s))
                prix_clean.append(float(p))
                
        if len(surfaces_clean) < 10:
            continue
            
        alpha, beta = least_squares_fit(surfaces_clean, prix_clean)
        r2 = r_squared(alpha, beta, surfaces_clean, prix_clean)
        
        prix_moyen = sum(prix_clean) / len(prix_clean)
        surf_moyenne = sum(surfaces_clean) / len(surfaces_clean)
        prix_m2_moyen = prix_moyen / surf_moyenne if surf_moyenne > 0 else 0
        
        resultats.append({
            'section': str(q),
            'quartier': QUARTIERS.get(q, f"Section {q}"),
            'nb_biens': len(surfaces_clean),
            'r2': float(r2),
            'prix_moyen': int(prix_moyen),
            'prix_m2': int(prix_m2_moyen),
            'alpha': float(alpha),
            'beta': float(beta)
        })
        
    return resultats

# ═══════════════════════════════════════════════════════════════
# EXÉCUTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("🚀 DÉMARRAGE DE LA PRÉPARATION DES DONNÉES FRONT-END")
    print("=" * 60)
    
    # 1. Chargement des données
    chemin_csv = "data/dvf_toulon.csv"
    if not os.path.exists(chemin_csv):
        print(f"❌ Erreur : Le fichier {chemin_csv} est introuvable.")
        return
        
    df = pd.read_csv(chemin_csv)
    print(f"✅ Fichier chargé : {len(df)} transactions.")
    
    # 2. Analyses globales
    res_apparts = analyser_type_bien(df, "Appartement", 3500, 10000)
    res_maisons = analyser_type_bien(df, "Maison", 2000, 6000)
    
    # 3. Analyses par quartier
    quartiers_apparts = regression_par_quartier(df, "Appartement")
    quartiers_maisons = regression_par_quartier(df, "Maison")
    
    # 4. Compilation des opportunités
    toutes_opportunites = []
    if res_apparts:
        toutes_opportunites.extend(res_apparts['opportunites'])
    if res_maisons:
        toutes_opportunites.extend(res_maisons['opportunites'])
        
    toutes_opportunites.sort(key=lambda x: x['economie'], reverse=True)
    
    # 5. Construction du Payload JSON final
    payload = {
        "modeles_globaux": {
            "appartements": {
                "alpha": res_apparts['alpha'],
                "beta": res_apparts['beta'],
                "r2": res_apparts['r2'],
                "nb_biens": res_apparts['nb_biens']
            } if res_apparts else None,
            "maisons": {
                "alpha": res_maisons['alpha'],
                "beta": res_maisons['beta'],
                "r2": res_maisons['r2'],
                "nb_biens": res_maisons['nb_biens']
            } if res_maisons else None
        },
        "donnees_quartiers": {
            "appartements": quartiers_apparts,
            "maisons": quartiers_maisons
        },
        "top_opportunites": toutes_opportunites[:20] # On limite aux 20 meilleures pour le front
    }
    
    # 6. Sauvegarde JSON
    dossier_sortie = 'donnees'
    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_json = os.path.join(dossier_sortie, 'modeles_regression.json')
    
    with open(chemin_json, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    print("=" * 60)
    print(f"✅ SUCCÈS : Données générées et sauvegardées dans {chemin_json}")
    print("=" * 60)

if __name__ == "__main__":
    main()