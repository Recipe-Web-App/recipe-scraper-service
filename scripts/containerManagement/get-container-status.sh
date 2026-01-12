#!/bin/bash
# scripts/containerManagement/get-container-status.sh
# Display comprehensive status of recipe-scraper-service deployment

set -euo pipefail

NAMESPACE="recipe-scraper-dev"

COLUMNS=$(tput cols 2>/dev/null || echo 80)

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_separator() {
  local char="${1:-=}"
  local width="${COLUMNS:-80}"
  printf '%*s\n' "$width" '' | tr ' ' "$char"
}

print_status() {
  local status="$1"
  local message="$2"
  if [ "$status" = "ok" ]; then
    echo -e "${GREEN}[OK]${NC} $message"
  elif [ "$status" = "warning" ]; then
    echo -e "${YELLOW}[WARN]${NC} $message"
  else
    echo -e "${RED}[ERROR]${NC} $message"
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

print_separator "="
echo -e "${CYAN}Recipe Scraper Service - Status Dashboard${NC}"
print_separator "="

# Check prerequisites
print_separator "-"
echo -e "${CYAN}Prerequisites:${NC}"
for cmd in kubectl minikube docker jq; do
  if command_exists "$cmd"; then
    print_status "ok" "$cmd is available"
  else
    print_status "warning" "$cmd is not installed"
  fi
done

# Check Minikube status
print_separator "-"
echo -e "${CYAN}Minikube Status:${NC}"
if minikube status >/dev/null 2>&1; then
  print_status "ok" "Minikube is running"
  MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "N/A")
  echo "  IP: $MINIKUBE_IP"
else
  print_status "error" "Minikube is not running"
  exit 1
fi

# Check namespace
print_separator "-"
echo -e "${CYAN}Namespace Status:${NC}"
if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  print_status "ok" "Namespace '$NAMESPACE' exists"
else
  print_status "error" "Namespace '$NAMESPACE' does not exist"
  echo ""
  echo "Run ./scripts/containerManagement/deploy-container.sh to deploy"
  exit 1
fi

# Deployments
print_separator "-"
echo -e "${CYAN}Deployments:${NC}"
kubectl get deployments -n "$NAMESPACE" -o wide 2>/dev/null || echo "No deployments found"

# Pods
print_separator "-"
echo -e "${CYAN}Pods:${NC}"
kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null || echo "No pods found"

# Pod restart counts
print_separator "-"
echo -e "${CYAN}Pod Restart Counts:${NC}"
kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.containerStatuses[*]}{.restartCount}{" restarts"}{end}{"\n"}{end}' 2>/dev/null || echo "Unable to get restart counts"

# Services
print_separator "-"
echo -e "${CYAN}Services:${NC}"
kubectl get services -n "$NAMESPACE" 2>/dev/null || echo "No services found"

# ConfigMaps
print_separator "-"
echo -e "${CYAN}ConfigMaps:${NC}"
kubectl get configmaps -n "$NAMESPACE" 2>/dev/null || echo "No configmaps found"

# Secrets
print_separator "-"
echo -e "${CYAN}Secrets:${NC}"
kubectl get secrets -n "$NAMESPACE" 2>/dev/null || echo "No secrets found"

# HPA
print_separator "-"
echo -e "${CYAN}Horizontal Pod Autoscaler:${NC}"
kubectl get hpa -n "$NAMESPACE" 2>/dev/null || echo "No HPA found"

# Ingress
print_separator "-"
echo -e "${CYAN}Ingress:${NC}"
kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo "No ingress found"

# Health Check
print_separator "-"
echo -e "${CYAN}Health Check (via kubectl exec):${NC}"

API_POD=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$API_POD" ]; then
  echo "  Testing /api/v1/recipe-scraper/health..."
  HEALTH_RESPONSE=$(kubectl exec -n "$NAMESPACE" "$API_POD" -- curl -s http://localhost:8000/api/v1/recipe-scraper/health 2>/dev/null || echo '{"error": "failed"}')

  if command_exists jq; then
    echo "$HEALTH_RESPONSE" | jq -r '
            if .status then
                "  Status: \(.status)\n  Version: \(.version)\n  Environment: \(.environment)"
            else
                "  Error: \(.error // "Unknown error")"
            end
        ' 2>/dev/null || echo "  Response: $HEALTH_RESPONSE"
  else
    echo "  Response: $HEALTH_RESPONSE"
  fi

  echo ""
  echo "  Testing /api/v1/recipe-scraper/ready..."
  READY_RESPONSE=$(kubectl exec -n "$NAMESPACE" "$API_POD" -- curl -s http://localhost:8000/api/v1/recipe-scraper/ready 2>/dev/null || echo '{"error": "failed"}')

  if command_exists jq; then
    echo "$READY_RESPONSE" | jq -r '
            if .status then
                "  Status: \(.status)\n  Dependencies: \(.dependencies | to_entries | map("    \(.key): \(.value)") | join("\n"))"
            else
                "  Error: \(.error // "Unknown error")"
            end
        ' 2>/dev/null || echo "  Response: $READY_RESPONSE"
  else
    echo "  Response: $READY_RESPONSE"
  fi
else
  print_status "warning" "No API pod available for health check"
fi

# Recent Events
print_separator "-"
echo -e "${CYAN}Recent Events (last 10):${NC}"
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' 2>/dev/null | tail -10 || echo "No events found"

# Recent Logs
print_separator "-"
echo -e "${CYAN}Recent API Logs (last 10 lines):${NC}"
kubectl logs -n "$NAMESPACE" -l app.kubernetes.io/component=api --tail=10 2>/dev/null || echo "No logs available"

print_separator "="
echo -e "${CYAN}Quick Commands:${NC}"
echo "  Port forward:  kubectl port-forward -n $NAMESPACE svc/recipe-scraper-service 8080:80"
echo "  Follow logs:   kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=api -f"
echo "  Exec into pod: kubectl exec -n $NAMESPACE -it \$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}') -- /bin/bash"
print_separator "="
