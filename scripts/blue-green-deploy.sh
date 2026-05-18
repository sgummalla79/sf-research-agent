#!/usr/bin/env bash
# blue-green-deploy.sh — rolling deploy for the UI.
#
# Usage:
#   blue-green-deploy.sh <image-tag> <repo-owner>
#
# The API uses its own blue-green deploy — see sgummalla79/pragna-api.
#
set -euo pipefail

VERSION="${1:-}"
OWNER="${2:-sgummalla79}"

if [ -z "$VERSION" ]; then
  echo "Usage: $0 <image-tag> [repo-owner]" >&2
  exit 1
fi

NS="pragna"
IMAGE_UI="ghcr.io/${OWNER}/pragna-ui:${VERSION}"

echo "=== UI Deploy: v${VERSION} ==="
echo "    Image (ui) : ${IMAGE_UI}"
echo ""

echo "=== Updating pragna-ui image ==="
kubectl set image deployment/pragna-ui \
  pragna-ui="${IMAGE_UI}" \
  -n "$NS"
kubectl rollout status deployment/pragna-ui -n "$NS" --timeout=120s

echo "=== Post-deploy health check (120s window) ==="
HEALTHY=false
for i in $(seq 1 12); do
  STATUS=$(curl -s -o /tmp/health.json -w "%{http_code}" \
    https://pragna.sgummallaworks.com/health 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "    ✓ Health check passed (attempt $i)"
    HEALTHY=true
    break
  fi
  echo "    Attempt $i: HTTP $STATUS — retrying in 10s..."
  sleep 10
done

if [ "$HEALTHY" = "false" ]; then
  echo "  ✗ Health check failed after deploy"
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  UI deployed: v${VERSION}"
echo "══════════════════════════════════════════════════"
