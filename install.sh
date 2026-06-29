#!/usr/bin/env bash
# Installe la configuration OpenCode Onyxia au niveau GLOBAL (~/.config/opencode),
# donc valable pour TOUS les projets et tous les services.
#
# Usage :  ./install.sh
# Cible personnalisable :  OPENCODE_CONFIG_DIR=/chemin ./install.sh
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

echo "→ Installation globale de la config OpenCode Onyxia dans : $DEST"
mkdir -p "$DEST/prompts" "$DEST/skills"

# Sauvegarde d'une éventuelle config existante (config + AGENTS.md)
if [ -f "$DEST/opencode.jsonc" ] || [ -f "$DEST/opencode.json" ] || [ -f "$DEST/AGENTS.md" ]; then
  ts="$(date +%Y%m%d-%H%M%S)"
  bak="$DEST/backup-$ts"
  echo "  Config existante détectée → sauvegarde dans $bak"
  mkdir -p "$bak"
  cp -f "$DEST"/opencode.json*  "$bak/" 2>/dev/null || true
  cp -f "$DEST"/AGENTS.md       "$bak/" 2>/dev/null || true
fi

# Copie : config + contexte + prompts + skills
#  (les skills GLOBALES vont dans ~/.config/opencode/skills/, sans le préfixe .opencode)
cp -f  "$SRC/opencode.jsonc"        "$DEST/opencode.jsonc"
cp -f  "$SRC/AGENTS.md"             "$DEST/AGENTS.md"
cp -rf "$SRC/prompts/."             "$DEST/prompts/"
cp -rf "$SRC/.opencode/skills/."    "$DEST/skills/"

echo "✓ Installé."
echo
echo "Étapes restantes (une seule fois) :"
echo "  export OPENAI_BASE_URL=\"https://llm.lab.sspcloud.fr/v1\""
echo "  export OPENAI_API_KEY=\"sk-……\"   # clé Open WebUI"
echo "Puis, depuis n'importe quel projet :  opencode  →  /models"
