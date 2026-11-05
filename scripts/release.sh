#!/usr/bin/env bash
# Publish the SHENNONG weights as a GitHub release (no HF token in this environment).
# Usage: scripts/release.sh v0.1.0
set -euo pipefail
cd "$(dirname "$0")/.."
TAG=${1:-v0.1.0}
REPO=${REPO:-cptlight/shennong}

test -s artifacts/shennong-mini-f16.gguf || { echo "no GGUF: run 'make export' first"; exit 1; }
SIZE=$(stat -f%z artifacts/shennong-mini-f16.gguf 2>/dev/null || stat -c%s artifacts/shennong-mini-f16.gguf)
if [ "$SIZE" -ge 1000000000 ]; then echo "REFUSING: $SIZE bytes exceeds the 1 GB constraint"; exit 1; fi

gh release create "$TAG" \
  --repo "$REPO" \
  --title "SHENNONG $TAG — open weights (<1 GB)" \
  --notes-file RELEASE_NOTES.md \
  artifacts/shennong-mini-f16.gguf \
  artifacts/shennong-mini-f16.gguf.sha256
echo "released $TAG ($SIZE bytes)"
