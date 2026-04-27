import pandas as pd

df = pd.read_csv("donnees/dvf-nettoyer_800_day.csv")

# Filtrer appartements
df = df[df['type_local'] == 'Appartement']

print("=" * 80)
print("INVESTIGATION APPARTEMENTS")
print("=" * 80)

# Vérifier les colonnes de surface disponibles
print("\nCOLONNES SURFACE DISPONIBLES :")
colonnes_surface = [col for col in df.columns if 'surface' in col.lower()]
for col in colonnes_surface:
    print(f"  • {col}")

# Stats surface_reelle_bati
print(f"\nSTATS surface_reelle_bati :")
print(df['surface_reelle_bati'].describe())

# Calculer prix/m²
df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']

print(f"\nSTATS PRIX/M² (calculé) :")
print(df['prix_m2'].describe())

# Échantillon de 20 appartements
print(f"\n20 APPARTEMENTS ALÉATOIRES :")
echantillon = df.sample(20)[['valeur_fonciere', 'surface_reelle_bati', 'prix_m2', 'nombre_pieces_principales']]
print(echantillon.to_string())

# Vérifier s'il y a une autre colonne surface
if 'lot1_surface_carrez' in df.columns:
    print(f"\n⚠️  ATTENTION : Colonne lot1_surface_carrez existe aussi !")
    print(f"   Stats lot1_surface_carrez :")
    print(df['lot1_surface_carrez'].describe())
    
    # Comparer les deux
    print(f"\n   COMPARAISON surface_reelle_bati vs lot1_surface_carrez :")
    comp = df[['surface_reelle_bati', 'lot1_surface_carrez']].head(10)
    print(comp.to_string())

# Corrélation prix/surface
from stats import correlation
corr = correlation(
    df['surface_reelle_bati'].tolist(),
    df['valeur_fonciere'].tolist()
)
print(f"\nCORRÉLATION prix/surface : {corr:.4f}")
print(f"(Devrait être entre 0.6 et 0.9 pour que la régression marche)")

print("\n" + "=" * 80)