#!/usr/bin/env bash
# Builds the release tarball: only the runtime files listed in MANIFEST (tracked by Git), under a versioned prefix.
#
# Usage:  scripts/build_dist.sh <version> [out_dir]     e.g.  scripts/build_dist.sh v1.2.0
# Writes: <out_dir>/opencode-onyxia.tar.gz          (asset name is the same in every release, so
#         <out_dir>/opencode-onyxia.tar.gz.sha256    releases/latest/download/... always resolves)
#         <out_dir>/onyxia-init.sh                   (attached to the release for reference)
#
# Content = the working-tree version of the files Git tracks under MANIFEST paths (untracked files, caches and
# local junk never get in). Reproducible: sorted entries, fixed mtime (last commit), root owner, gzip -n.
set -euo pipefail

VERSION="${1:?usage: scripts/build_dist.sh <version> [out_dir]}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${2:-$REPO/dist}"
NAME="opencode-onyxia"
PREFIX="$NAME-$VERSION"

cd "$REPO"
mapfile -t paths < <(grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' MANIFEST)
mapfile -t files < <(git ls-files -- "${paths[@]}")
for p in "${paths[@]}"; do   # a typo or a removed path in MANIFEST must not silently ship an incomplete tarball
  if ! printf '%s\n' "${files[@]}" | grep -q -e "^$p\$" -e "^$p/"; then
    echo "✗ MANIFEST path not tracked by Git: $p" >&2
    exit 1
  fi
done

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
printf '%s\n' "$VERSION" > "$stage/VERSION"
mtime="@$(git log -1 --format=%ct)"
tar_opts=(--sort=name --mtime="$mtime" --owner=0 --group=0 --numeric-owner --mode='u+rw,go+r,go-w')

mkdir -p "$OUT"
{
  tar -cf - "${tar_opts[@]}" --transform "s|^|$PREFIX/|" "${files[@]}"
} > "$stage/files.tar"
tar -rf "$stage/files.tar" "${tar_opts[@]}" -C "$stage" --transform "s|^|$PREFIX/|" VERSION
gzip -n -9 < "$stage/files.tar" > "$OUT/$NAME.tar.gz"
(cd "$OUT" && sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256")
cp -f "$REPO/onyxia-init.sh" "$OUT/onyxia-init.sh"

echo "✓ $OUT/$NAME.tar.gz  ($PREFIX, ${#files[@]} files)"
cat "$OUT/$NAME.tar.gz.sha256"
