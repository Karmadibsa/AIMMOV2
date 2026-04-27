import pandas as pd

from analysis.stats import mean, correlation, median
from analysis.regression import least_squares_fit

import math

# 1. Charger les données (Pandas est autorisé pour la lecture, pas pour les calculs)

df = pd.read_csv("data/dvf_toulon.csv")

# On repasse en listes Python pour les calculs statistiques
prix_bruts = df['valeur_fonciere'].tolist()
surfaces_brutes = df['surface_reelle_bati'].tolist()

# 2. NETTOYAGE des données : on ignore les points où le prix ou la surface est manquante (NaN)
prix = []
surfaces = []
for p, s in zip(prix_bruts, surfaces_brutes):
    if not math.isnan(p) and not math.isnan(s):
        prix.append(p)
        surfaces.append(s)

# Calcul des KPIs
prix_moyen = mean(prix)
correlation_prix_surface = correlation(prix, surfaces)

prix_m2 = [p / s for p, s in zip(prix, surfaces) if s > 0]
prix_moyen_m2 = mean(prix_m2)
prix_median_m2 = median(prix_m2)


# Taux d'accessibilité pour les primo-accédants
biens_accessibles = [p for p in prix if p <= 450000]
taux_accessibilite = len(biens_accessibles) / len(prix) if len(prix) > 0 else 0


# Affichage des résultats
print(f"Prix moyen d'un logement : {prix_moyen:.2f} euros")
print(f"Correlation entre prix et surface : {correlation_prix_surface:.2f}")
print(f"Prix moyen au m2 : {prix_moyen_m2:.2f} euros/m2")
print(f"Prix median au m2 : {prix_median_m2:.2f} euros/m2")
print(f"Taux d'accessibilité (biens <= 450k€) : {taux_accessibilite:.2%}")
print(f"Nombre total de biens inférieur 450k€ : {len(biens_accessibles)}")