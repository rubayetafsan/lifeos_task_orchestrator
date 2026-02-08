#!/bin/bash
set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="lifeos-task-orchestrator"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== LifeOS Task Orchestrator - GCP Deployment ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Checking prerequisites..."
if ! command_exists gcloud; then
    echo "Error: gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command_exists docker; then
    echo "Error: Docker not found. Please install Docker."
    exit 1
fi

echo "✓ Prerequisites satisfied"
echo ""

# Set GCP project
echo "Setting GCP project..."
gcloud config set project ${PROJECT_ID}
echo ""

# Enable required APIs
echo "Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    pubsub.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com
echo "✓ APIs enabled"
echo ""

# Build and push Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:latest .
echo "✓ Image built"
echo ""

echo "Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}:latest
echo "✓ Image pushed"
echo ""

# Create Cloud SQL instance (if not exists)
echo "Checking for Cloud SQL instance..."
if ! gcloud sql instances describe ${SERVICE_NAME}-db --project=${PROJECT_ID} 2>/dev/null; then
    echo "Creating Cloud SQL instance..."
    gcloud sql instances create ${SERVICE_NAME}-db \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=${REGION} \
        --root-password=change-me-in-production
    
    echo "Creating database..."
    gcloud sql databases create lifeos \
        --instance=${SERVICE_NAME}-db
    echo "✓ Cloud SQL instance created"
else
    echo "✓ Cloud SQL instance already exists"
fi
echo ""

# Create Pub/Sub topics (if not exists)
echo "Creating Pub/Sub topics..."
gcloud pubsub topics create task-events --project=${PROJECT_ID} 2>/dev/null || echo "✓ task-events topic exists"
gcloud pubsub topics create workflow-events --project=${PROJECT_ID} 2>/dev/null || echo "✓ workflow-events topic exists"
echo ""

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=${PROJECT_ID}" \
    --min-instances=1 \
    --max-instances=10 \
    --cpu=2 \
    --memory=2Gi \
    --timeout=300 \
    --concurrency=80

echo ""
echo "=== Deployment Complete ==="
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${REGION} --format 'value(status.url)')
echo "Service URL: ${SERVICE_URL}"
echo "API Docs: ${SERVICE_URL}/docs"
echo "Health: ${SERVICE_URL}/api/v1/health"
echo ""
echo "Next steps:"
echo "1. Configure database connection string in Secret Manager"
echo "2. Set up proper SECRET_KEY in Secret Manager"
echo "3. Configure custom domain (optional)"
echo "4. Set up monitoring and alerting"
