#!/usr/bin/env bash
# blue-green-deploy.sh — blue-green deploy for the UI.
#
# Usage:
#   blue-green-deploy.sh <namespace> <image> <health-url>
#
# Example:
#   blue-green-deploy.sh pragna ghcr.io/sgummalla79/pragna-ui:1.2.3 https://pragna.sgummallaworks.com/
#   blue-green-deploy.sh pragna-staging ghcr.io/sgummalla79/pragna-ui:staging-abc123 https://pragna-staging.sgummallaworks.com/
#
# The API uses its own blue-green deploy — see sgummalla79/pragna-api.
#
set -euo pipefail

NS="${1:-}"
IMAGE="${2:-}"
HEALTH_URL="${3:-}"

if [ -z "$NS" ] || [ -z "$IMAGE" ] || [ -z "$HEALTH_URL" ]; then
  echo "Usage: $0 <namespace> <image> <health-url>" >&2
  exit 1
fi

# ── Detect active slot ────────────────────────────────────────────────────────
ACTIVE=$(kubectl get service pragna-ui -n "$NS" \
  -o jsonpath='{.spec.selector.slot}' 2>/dev/null || echo "blue")

if [ "$ACTIVE" = "blue" ]; then
  INACTIVE="green"
else
  INACTIVE="blue"
fi

echo "=== Blue-Green Deploy ==="
echo "    Namespace  : ${NS}"
echo "    Image      : ${IMAGE}"
echo "    Active slot: ${ACTIVE}  (stays live until cutover)"
echo "    Target slot: ${INACTIVE}"
echo ""

# ── Deploy to inactive slot ───────────────────────────────────────────────────
echo "--- Updating pragna-ui-${INACTIVE} ---"
kubectl set image deployment/pragna-ui-${INACTIVE} \
  pragna-ui="${IMAGE}" \
  -n "$NS"

echo "--- Waiting for pragna-ui-${INACTIVE} rollout ---"
kubectl rollout status deployment/pragna-ui-${INACTIVE} \
  -n "$NS" --timeout=120s

# ── Switch service to inactive slot ──────────────────────────────────────────
echo "--- Cutting over service to ${INACTIVE} ---"
kubectl patch service pragna-ui -n "$NS" \
  -p "{\"spec\":{\"selector\":{\"app\":\"pragna-ui\",\"slot\":\"${INACTIVE}\"}}}"

# ── Post-cutover health check ─────────────────────────────────────────────────
echo "--- Health check (120s window) ---"
HEALTHY=false
for i in $(seq 1 12); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "    ✓ Healthy (attempt $i)"
    HEALTHY=true
    break
  fi
  echo "    Attempt $i: HTTP $STATUS — retrying in 10s..."
  sleep 10
done

# ── Rollback on failure ───────────────────────────────────────────────────────
if [ "$HEALTHY" = "false" ]; then
  echo ""
  echo "--- Health check failed — rolling back to ${ACTIVE} ---"
  kubectl patch service pragna-ui -n "$NS" \
    -p "{\"spec\":{\"selector\":{\"app\":\"pragna-ui\",\"slot\":\"${ACTIVE}\"}}}"
  echo "  ✗ Rollback complete. ${ACTIVE} slot is live. Investigate ${INACTIVE}."
  exit 1
fi

echo ""
echo "════════════════════════════════════════════════"
echo "  Deployed to ${INACTIVE} slot — now live"
echo "  Previous slot (${ACTIVE}) on standby for next deploy"
echo "════════════════════════════════════════════════"
