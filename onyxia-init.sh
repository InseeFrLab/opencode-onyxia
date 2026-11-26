#!/usr/bin/env bash
# SSP Cloud / Onyxia init script: installs opencode v2 (if needed) and the opencode-onyxia config from a release.
#
# As your personal init script (Onyxia → My account → Services → Initialization script):
#   URL   https://raw.githubusercontent.com/inseefrlab/opencode-onyxia/main/onyxia-init.sh
#   args  e.g.  --version v1.0.0 --bare
#   (Onyxia runs `curl $URL | bash -s -- $ARGS` WITHOUT -L: use a raw.githubusercontent.com URL, never a
#    github.com/.../releases/... one, which redirects and would run nothing.)
# From another init script (Onyxia takes only one):
#   curl -fsSL https://raw.githubusercontent.com/inseefrlab/opencode-onyxia/main/onyxia-init.sh | bash -s -- --version v1.0.0
#
# Options:  --version <tag>   release to install (default: latest; env OPENCODE_ONYXIA_VERSION)
#           anything else      passed to install.sh (--bare, --claude)
# Env:      OPENCODE_ONYXIA_REPO          GitHub repo to download from (default inseefrlab/opencode-onyxia)
#           OPENCODE_ONYXIA_URL           base URL holding opencode-onyxia.tar.gz(.sha256): overrides repo/version
#           OPENCODE_ONYXIA_SKIP_OPENCODE=1  do not install opencode itself
#           OPENCODE_CONFIG_DIR           target config dir (default ~/.config/opencode, handled by install.sh)
#
# Never makes the service fail: any error is logged (~/.cache/opencode-onyxia-init.log) and the script exits 0.
set -uo pipefail

LOG="${HOME}/.cache/opencode-onyxia-init.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null && exec > >(tee -a "$LOG") 2>&1
echo "=== opencode-onyxia init — $(date -Is) ==="

log()  { echo "[opencode-onyxia] $*"; }
fail() { echo "[opencode-onyxia] ✗ $*" >&2; return 1; }

is_v2() { command -v opencode >/dev/null 2>&1 && opencode --version 2>/dev/null | head -n1 | grep -Eq '(^|v| )2\.'; }

ensure_path_line() {  # $1 = directory to put on PATH in ~/.bashrc (idempotent)
  local line="export PATH=\"$1:\$PATH\""
  grep -qxF "$line" "$HOME/.bashrc" 2>/dev/null || echo "$line" >> "$HOME/.bashrc"
  case ":$PATH:" in *":$1:"*) ;; *) export PATH="$1:$PATH" ;; esac
}

install_opencode() {
  if [ "${OPENCODE_ONYXIA_SKIP_OPENCODE:-0}" = 1 ]; then log "skipping opencode install (OPENCODE_ONYXIA_SKIP_OPENCODE=1)"; return 0; fi
  if is_v2; then log "opencode already installed: $(opencode --version 2>/dev/null | head -n1)"; return 0; fi
  log "installing opencode v2…"
  curl -fsSL https://opencode.ai/v2/install | bash || fail "opencode installer failed" || return 1
  local d
  for d in "$HOME/.opencode/bin" "$HOME/.local/bin"; do
    [ -x "$d/opencode" ] && ensure_path_line "$d"
  done
  is_v2 || fail "opencode v2 not found on PATH after install" || return 1
  log "opencode installed: $(opencode --version 2>/dev/null | head -n1)"
}

install_config() {
  local version="${OPENCODE_ONYXIA_VERSION:-latest}" repo="${OPENCODE_ONYXIA_REPO:-inseefrlab/opencode-onyxia}"
  local args=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --version) [ $# -ge 2 ] || { fail "--version needs a value"; return 1; }; version="$2"; shift 2 ;;
      --version=*) version="${1#*=}"; shift ;;
      *) args+=("$1"); shift ;;
    esac
  done

  local base
  if [ -n "${OPENCODE_ONYXIA_URL:-}" ]; then base="$OPENCODE_ONYXIA_URL"
  elif [ "$version" = latest ]; then base="https://github.com/$repo/releases/latest/download"
  else base="https://github.com/$repo/releases/download/$version"
  fi

  tmp="$(mktemp -d)" || return 1   # global: removed by the EXIT trap
  log "downloading $base/opencode-onyxia.tar.gz"
  curl -fsSL -o "$tmp/opencode-onyxia.tar.gz" "$base/opencode-onyxia.tar.gz" \
    && curl -fsSL -o "$tmp/opencode-onyxia.tar.gz.sha256" "$base/opencode-onyxia.tar.gz.sha256" \
    || { fail "download failed (version '$version' exists? network?)"; return 1; }
  (cd "$tmp" && sha256sum -c --quiet opencode-onyxia.tar.gz.sha256) || { fail "checksum mismatch: not installing"; return 1; }

  mkdir "$tmp/src" && tar -xzf "$tmp/opencode-onyxia.tar.gz" -C "$tmp/src" --strip-components=1 \
    || { fail "could not extract the tarball"; return 1; }
  local installed
  installed="$(cat "$tmp/src/VERSION" 2>/dev/null || echo unknown)"
  log "installing config $installed ${args[*]:-}"
  bash "$tmp/src/install.sh" "${args[@]}" || { fail "install.sh failed"; return 1; }

  # When Onyxia runs this as root, hand the files back to the service user
  local dest="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
  if [ "$(id -u)" = 0 ] && [ -n "${USERNAME:-}" ] && id "$USERNAME" >/dev/null 2>&1; then
    chown -R "$USERNAME:$(id -gn "$USERNAME")" "$dest" "$HOME/.claude" 2>/dev/null || true
  fi
  log "✓ opencode-onyxia $installed installed in $dest"
}

check_env() {
  if [ -z "${OPENAI_BASE_URL:-}" ] || [ -z "${OPENAI_API_KEY:-}" ]; then
    log "⚠ OPENAI_BASE_URL / OPENAI_API_KEY not set: opencode cannot reach the models."
    log "  Create a key at https://llm.lab.sspcloud.fr (Settings → Account → API Keys), store it in Vault"
    log "  (My secrets) and inject it in your services; OPENAI_BASE_URL=https://llm.lab.sspcloud.fr/api"
  fi
}

tmp=""
trap '[ -n "$tmp" ] && rm -rf "$tmp"' EXIT
install_opencode || log "continuing without a verified opencode v2"
if install_config "$@"; then check_env; else log "config NOT installed — see $LOG"; fi
exit 0
