import pandas as pd

df = pd.read_csv("../donnees/dvf-nettoyer_800_day.csv")

print("=" * 80)
print("ANALYSE DU DATASET DVF")
print("=" * 80)

# 1. Liste des colonnes
print("\n1. COLONNES DISPONIBLES :")
print(df.columns.tolist())

# 2. Nombre de lignes
print(f"\n2. NOMBRE DE LIGNES : {len(df)}")

# 3. Exemple de 5 lignes
print("\n3. EXEMPLE DE 5 PREMIÈRES LIGNES :")
colonnes_importantes = ['valeur_fonciere', 'surface_reelle_bati']
# Ajouter type_bien si existe
if 'type_bien' in df.columns:
    colonnes_importantes.append('type_bien')
if 'nature_mutation' in df.columns:
    colonnes_importantes.append('nature_mutation')
if 'nombre_pieces_principales' in df.columns:
    colonnes_importantes.append('nombre_pieces_principales')
if 'code_commune' in df.columns:
    colonnes_importantes.append('code_commune')

print(df[colonnes_importantes].head(5))

# 4. Types de biens (si existe)
if 'type_bien' in df.columns:
    print("\n4. RÉPARTITION PAR TYPE DE BIEN :")
    print(df['type_bien'].value_counts())
else:
    print("\n4. ⚠️  Colonne 'type_bien' absente")

# 5. Statistiques prix
print("\n5. STATISTIQUES VALEUR FONCIÈRE :")
print(df['valeur_fonciere'].describe())

# 6. Statistiques surface
print("\n6. STATISTIQUES SURFACE :")
print(df['surface_reelle_bati'].describe())

# 7. Prix/m²
df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']
print("\n7. STATISTIQUES PRIX/M² :")
print(df['prix_m2'].describe())

# 8. Échantillon aléatoire
print("\n8. 10 TRANSACTIONS ALÉATOIRES :")
echantillon = df.sample(min(10, len(df)))[colonnes_importantes + ['prix_m2']]
print(echantillon)

# 9. Vérifier les valeurs bizarres
print("\n9. VALEURS POTENTIELLEMENT BIZARRES :")
print(f"   • Prix < 50 000€ : {len(df[df['valeur_fonciere'] < 50000])} transactions")
print(f"   • Prix > 1 000 000€ : {len(df[df['valeur_fonciere'] > 1000000])} transactions")
print(f"   • Surface < 20m² : {len(df[df['surface_reelle_bati'] < 20])} transactions")
print(f"   • Surface > 200m² : {len(df[df['surface_reelle_bati'] > 200])} transactions")
print(f"   • Prix/m² < 1000€ : {len(df[df['prix_m2'] < 1000])} transactions")
print(f"   • Prix/m² > 8000€ : {len(df[df['prix_m2'] > 8000])} transactions")

print("\n" + "=" * 80)