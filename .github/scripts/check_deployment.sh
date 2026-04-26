#!/usr/bin/env bash
# Extrait l'URL déployée du README et vérifie qu'elle répond en HTTP 200.
set -euo pipefail

README="README.md"

# Cherche la première URL https:// dans le README qui n'est pas github.com
URL=$(grep -oP 'https://[^\s\)>"]+' "$README" \
  | grep -v "github\.com" \
  | grep -v "supabase\.co" \
  | head -1 || true)

if [ -z "$URL" ]; then
  echo "❌ Aucune URL déployée trouvée dans README.md"
  echo "   Ajouter l'URL de l'application (Railway, HF Spaces, Render...)"
  exit 1
fi

echo "→ URL détectée : $URL"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$URL" || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
  echo "✅ $URL répond ($HTTP_CODE)"
  exit 0
else
  echo "❌ $URL ne répond pas correctement (HTTP $HTTP_CODE)"
  exit 1
fi
