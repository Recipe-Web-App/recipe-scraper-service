#!/bin/bash
# scripts/containerManagement/deploy-container.sh

set -euo pipefail

CLUSTER_NAME="recipe-manager-system"
NAMESPACE="recipe-scraper"
CONFIG_DIR="k8s"
SECRET_NAME="recipe-scraper-db-password"
PASSWORD_ENV_VAR="POSTGRES_PASSWORD"
IMAGE_NAME="recipe-scraper-service"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Utility function for printing section separators
print_separator() {
  printf '%*s\n' "${COLUMNS:-80}" '' | tr ' ' '='
}

print_separator
echo "📂 Ensuring namespace '${NAMESPACE}' exists..."
print_separator

if ! minikube status >/dev/null 2>&1; then
  echo "🚀 Starting Minikube..."
  minikube start
else
  echo "✅ Minikube is already running."
fi

kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"

print_separator
echo "🔧 Loading environment variables from .env file (if present)..."
print_separator

if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

print_separator
echo "🐳 Building Docker image: ${FULL_IMAGE_NAME} (inside Minikube Docker daemon)"
print_separator

eval "$(minikube docker-env)"
docker build -t "$FULL_IMAGE_NAME" .

print_separator
echo "⚙️ Creating/Updating ConfigMap from env..."
print_separator

envsubst < "${CONFIG_DIR}/configmap-template.yaml" | kubectl apply -f -

print_separator
echo "🔐 Creating/updating Secret..."
print_separator

if [ -z "${!PASSWORD_ENV_VAR:-}" ]; then
  read -r -s -p "Enter recipe_scraper_user PostgreSQL password: " POSTGRES_PASSWORD
  echo
else
  POSTGRES_PASSWORD="${!PASSWORD_ENV_VAR}"
fi

kubectl delete secret "$SECRET_NAME" -n "$NAMESPACE" --ignore-not-found
envsubst < "${CONFIG_DIR}/secret.yaml" | kubectl apply -f -

print_separator
echo "📦 Deploying Recipe-Scraper container..."
print_separator

kubectl apply -f "${CONFIG_DIR}/deployment.yaml"

print_separator
echo "🌐 Exposing Recipe-Scraper via ClusterIP Service..."
print_separator

kubectl apply -f "${CONFIG_DIR}/service.yaml"

print_separator
echo "📥 Applying Ingress resource..."
print_separator

kubectl apply -f "${CONFIG_DIR}/ingress.yaml"

print_separator
echo "⏳ Waiting for Recipe-Scraper pod to be ready..."
print_separator

kubectl wait --namespace="$NAMESPACE" \
  --for=condition=Ready pod \
  --selector=app=recipe-scraper \
  --timeout=90s

print_separator
echo "✅ Recipe-Scraper app is up and running in namespace '$NAMESPACE'."
print_separator

print_separator
echo "🔗 Setting up /etc/hosts for recipe.local..."
print_separator

MINIKUBE_IP=$(minikube ip)
if grep -q "recipe.local" /etc/hosts; then
  echo "🔄 Updating /etc/hosts for recipe.local..."
  sed -i "/recipe.local/d" /etc/hosts
else
  echo "➕ Adding recipe.local to /etc/hosts..."
fi
echo "$MINIKUBE_IP recipe.local" >> /etc/hosts

print_separator
echo "🌍 You can now access your app at: http://recipe.local/api/recipe-scraper/health"
print_separator

POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=recipe-scraper -o jsonpath="{.items[0].metadata.name}")
SERVICE_JSON=$(kubectl get svc recipe-scraper -n "$NAMESPACE" -o json)
SERVICE_IP=$(echo "$SERVICE_JSON" | jq -r '.spec.clusterIP')
SERVICE_PORT=$(echo "$SERVICE_JSON" | jq -r '.spec.ports[0].port')
INGRESS_HOSTS=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[*].spec.rules[*].host}' | tr ' ' '\n' | sort -u | paste -sd ',' -)

print_separator
echo "📡 Access info:"
echo "  Pod: $POD_NAME"
echo "  Service: $SERVICE_IP:$SERVICE_PORT"
echo "  Ingress Hosts: $INGRESS_HOSTS"
echo "  Minikube IP: $MINIKUBE_IP (added to /etc/hosts as recipe.local)"
print_separator
