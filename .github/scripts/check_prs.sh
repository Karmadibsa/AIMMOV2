#!/usr/bin/env bash
# Vérifie qu'il y a au moins autant de PRs que de membres de l'équipe déclarés dans le README.
# Utilise l'API GitHub avec GITHUB_TOKEN (disponible automatiquement dans Actions).
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-}"
TOKEN="${GITHUB_TOKEN:-}"

if [ -z "$REPO" ] || [ -z "$TOKEN" ]; then
  echo "⚪ Vérification PRs ignorée (hors GitHub Actions)"
  exit 0
fi

# Compte les membres déclarés dans le README (lignes du tableau Équipe)
NB_MEMBRES=$(grep -c "Prénom NOM\|[A-Z][a-z]* [A-Z][A-Z]" README.md 2>/dev/null || echo 0)
# Fallback : on attend au moins 1 PR si on ne peut pas compter les membres
NB_MEMBRES_MIN=$(( NB_MEMBRES > 1 ? NB_MEMBRES : 1 ))

# Récupère le nombre de PRs (ouvertes + fermées)
NB_PRS=$(curl -s \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/pulls?state=all&per_page=100" \
  | python3 -c "import sys,json; prs=json.load(sys.stdin); print(len(prs))" 2>/dev/null || echo 0)

echo "→ PRs trouvées : $NB_PRS (minimum attendu : $NB_MEMBRES_MIN)"

if [ "$NB_PRS" -ge "$NB_MEMBRES_MIN" ]; then
  echo "✅ Git hygiene OK — $NB_PRS PR(s)"
  exit 0
else
  echo "❌ Pas assez de PRs — chaque membre doit ouvrir au moins 1 PR"
  echo "   Trouvé : $NB_PRS / Attendu : $NB_MEMBRES_MIN"
  exit 1
fi
