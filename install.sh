#!/usr/bin/env bash
# Installs the OpenCode Onyxia configuration GLOBALLY (~/.config/opencode),
# so it applies to ALL projects and all services.
#
# Usage:            ./install.sh
# Custom target:    OPENCODE_CONFIG_DIR=/path ./install.sh
# Claude Code too:  ./install.sh --claude   (also copies skills to ~/.claude/skills
#                                            so Claude Code picks them up)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

WITH_CLAUDE=false
for arg in "$@"; do
  case "$arg" in
    --claude) WITH_CLAUDE=true ;;
    *) echo "Unknown option: $arg" >&2; echo "Usage: ./install.sh [--claude]" >&2; exit 2 ;;
  esac
done

echo "→ Installing the OpenCode Onyxia config globally into: $DEST"
mkdir -p "$DEST/prompts" "$DEST/skills" "$DEST/command"

# Back up any existing config (config + AGENTS.md)
if [ -f "$DEST/opencode.jsonc" ] || [ -f "$DEST/opencode.json" ] || [ -f "$DEST/AGENTS.md" ]; then
  ts="$(date +%Y%m%d-%H%M%S)"
  bak="$DEST/backup-$ts"
  echo "  Existing config detected → backing it up to $bak"
  mkdir -p "$bak"
  cp -f "$DEST"/opencode.json*  "$bak/" 2>/dev/null || true
  cp -f "$DEST"/AGENTS.md       "$bak/" 2>/dev/null || true
fi

# Copy: config + context + prompts + skills + commands
#  (GLOBAL skills live in ~/.config/opencode/skills/, without the .opencode prefix)
cp -f  "$SRC/opencode.jsonc"        "$DEST/opencode.jsonc"
cp -f  "$SRC/AGENTS.md"             "$DEST/AGENTS.md"
cp -rf "$SRC/prompts/."             "$DEST/prompts/"
cp -rf "$SRC/.opencode/skills/."    "$DEST/skills/"
if [ -d "$SRC/.opencode/command" ]; then
  cp -rf "$SRC/.opencode/command/." "$DEST/command/"
fi

# Bundled skill scripts must stay executable
find "$DEST/skills" -type f \( -name "*.sh" -o -name "*.py" \) -path "*/scripts/*" \
  -exec chmod +x {} + 2>/dev/null || true

# Optional: expose the same skills to Claude Code (~/.claude/skills)
if [ "$WITH_CLAUDE" = true ]; then
  CLAUDE_SKILLS="$HOME/.claude/skills"
  echo "→ Also installing skills for Claude Code into: $CLAUDE_SKILLS"
  mkdir -p "$CLAUDE_SKILLS"
  cp -rf "$SRC/.opencode/skills/." "$CLAUDE_SKILLS/"
  find "$CLAUDE_SKILLS" -type f \( -name "*.sh" -o -name "*.py" \) -path "*/scripts/*" \
    -exec chmod +x {} + 2>/dev/null || true
  echo "  Tip: Claude Code reads project context from CLAUDE.md — consider copying"
  echo "  the relevant parts of AGENTS.md into ~/.claude/CLAUDE.md"
fi

echo "✓ Installed."
echo
echo "Remaining steps (one time only):"
echo "  export OPENAI_BASE_URL=\"https://llm.lab.sspcloud.fr/v1\""
echo "  export OPENAI_API_KEY=\"sk-……\"   # Open WebUI key"
echo "Then, from any project:  opencode  →  /models"
