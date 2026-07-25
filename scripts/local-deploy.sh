#!/usr/bin/env bash
#
# Build the image on this machine, load it into the local kind cluster
# and roll it out. This is the same sequence the CI pipeline runs, minus
# the registry push.
#
# Usage:  ./scripts/local-deploy.sh
#
set -euo pipefail

CLUSTER="${CLUSTER:-devsecops}"
IMAGE="secure-website:local"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT"

echo "==> Checking the cluster is up"
if ! kind get clusters | grep -qx "$CLUSTER"; then
  echo "Cluster '$CLUSTER' not found. Creating it."
  kind create cluster --name "$CLUSTER"
fi
kubectl cluster-info --context "kind-$CLUSTER" >/dev/null

echo "==> Building image"
docker build -t "$IMAGE" .

echo "==> Scanning image with Trivy"
if command -v trivy >/dev/null 2>&1; then
  mkdir -p reports
  trivy image --scanners vuln --severity HIGH,CRITICAL "$IMAGE" \
    | tee reports/trivy-report.txt
  trivy image --format cyclonedx --output reports/sbom.cyclonedx.json "$IMAGE"
  echo "    SBOM written to reports/sbom.cyclonedx.json"
else
  echo "    Trivy not installed locally, skipping. (brew install trivy)"
fi

echo "==> Loading image into the cluster"
kind load docker-image "$IMAGE" --name "$CLUSTER"

echo "==> Deploying"
TMP="$(mktemp -d)"
cp k8s/*.yaml "$TMP/"
sed -i '' "s|IMAGE_PLACEHOLDER|$IMAGE|g" "$TMP/deployment.yaml" 2>/dev/null \
  || sed -i "s|IMAGE_PLACEHOLDER|$IMAGE|g" "$TMP/deployment.yaml"
kubectl apply -f "$TMP/"
rm -rf "$TMP"

echo "==> Waiting for rollout"
kubectl rollout status deployment/secure-website --timeout=180s

echo
kubectl get pods -o wide
echo
echo "Done. To view the site:"
echo "  kubectl port-forward svc/secure-website 8080:80"
echo "  then open http://localhost:8080"
