# GCP Deployment Guide

Complete guide for deploying LifeOS Task Orchestrator to Google Cloud Platform.

## Prerequisites

1. **Google Cloud Account**
   - Active GCP account with billing enabled
   - Project created

2. **Local Tools**
   - gcloud CLI installed ([Download](https://cloud.google.com/sdk/docs/install))
   - Docker installed
   - Git

3. **Permissions**
   - Owner or Editor role on GCP project
   - Or specific roles:
     - Cloud Run Admin
     - Cloud SQL Admin
     - Secret Manager Admin
     - Pub/Sub Admin
     - Service Account User

## Step-by-Step Deployment

### 1. Initial Setup

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Login to gcloud
gcloud auth login

# Set project
gcloud config set project ${PROJECT_ID}

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  pubsub.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  logging.googleapis.com
```

### 2. Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create lifeos-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=${REGION} \
  --root-password=CHANGE_ME_SECURE_PASSWORD \
  --storage-type=SSD \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=03:00

# Create database
gcloud sql databases create lifeos \
  --instance=lifeos-db

# Create database user
gcloud sql users create lifeos-user \
  --instance=lifeos-db \
  --password=CHANGE_ME_SECURE_PASSWORD

# Get connection name
gcloud sql instances describe lifeos-db \
  --format='value(connectionName)'
# Save this for later: PROJECT_ID:REGION:lifeos-db
```

### 3. Set Up Secrets

```bash
# Generate secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create secrets
echo -n "postgresql://lifeos-user:YOUR_PASSWORD@/lifeos?host=/cloudsql/PROJECT_ID:REGION:lifeos-db" | \
  gcloud secrets create database-url --data-file=-

echo -n "${SECRET_KEY}" | \
  gcloud secrets create secret-key --data-file=-

# Grant access to Cloud Run
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding secret-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Create Pub/Sub Topics

```bash
# Create topics
gcloud pubsub topics create task-events
gcloud pubsub topics create workflow-events

# Create subscriptions
gcloud pubsub subscriptions create task-events-sub \
  --topic=task-events \
  --ack-deadline=60

gcloud pubsub subscriptions create workflow-events-sub \
  --topic=workflow-events \
  --ack-deadline=60
```

### 5. Build and Push Docker Image

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Build image
docker build -t gcr.io/${PROJECT_ID}/lifeos-task-orchestrator:latest .

# Push to Container Registry
docker push gcr.io/${PROJECT_ID}/lifeos-task-orchestrator:latest
```

### 6. Deploy to Cloud Run

```bash
# Deploy service
gcloud run deploy lifeos-task-orchestrator \
  --image gcr.io/${PROJECT_ID}/lifeos-task-orchestrator:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},LOG_LEVEL=INFO,JSON_LOGS=true" \
  --set-secrets="DATABASE_URL=database-url:latest,SECRET_KEY=secret-key:latest" \
  --add-cloudsql-instances=${PROJECT_ID}:${REGION}:lifeos-db \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=2 \
  --memory=2Gi \
  --timeout=300 \
  --concurrency=80 \
  --cpu-throttling=false

# Get service URL
SERVICE_URL=$(gcloud run services describe lifeos-task-orchestrator \
  --platform managed \
  --region ${REGION} \
  --format 'value(status.url)')

echo "Service deployed at: ${SERVICE_URL}"
```

### 7. Initialize Database

```bash
# Connect to Cloud SQL
gcloud sql connect lifeos-db --user=lifeos-user

# In psql prompt:
# \c lifeos
# Tables will be created automatically on first run
```

### 8. Verify Deployment

```bash
# Health check
curl ${SERVICE_URL}/api/v1/health

# API documentation
echo "API Docs: ${SERVICE_URL}/docs"

# Test creating a task
curl -X POST "${SERVICE_URL}/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Task",
    "task_type": "email",
    "input_data": {
      "action": "send",
      "to": "test@example.com",
      "subject": "Test"
    }
  }'
```

## Configuration

### Environment Variables

Set in Cloud Run:

| Variable | Description | Value |
|----------|-------------|-------|
| `ENVIRONMENT` | Environment name | production |
| `GCP_PROJECT_ID` | GCP project ID | your-project-id |
| `GCP_REGION` | GCP region | us-central1 |
| `LOG_LEVEL` | Logging level | INFO |
| `JSON_LOGS` | JSON log format | true |

### Secrets (Secret Manager)

| Secret | Description |
|--------|-------------|
| `database-url` | PostgreSQL connection string |
| `secret-key` | Application secret key (32+ chars) |

## Monitoring

### Cloud Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=lifeos-task-orchestrator" \
  --limit 50 \
  --format json
```

### Cloud Monitoring

1. Navigate to Cloud Console → Monitoring
2. Create dashboard with metrics:
   - Request count
   - Request latency
   - Error rate
   - Instance count
   - CPU utilization
   - Memory utilization

### Alerts

Create alerts for:

```bash
# Error rate alert
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s
```

## Scaling

### Auto-scaling Configuration

Current settings:
- Min instances: 1
- Max instances: 10
- Concurrency: 80 requests per instance

### Update scaling:

```bash
gcloud run services update lifeos-task-orchestrator \
  --min-instances=2 \
  --max-instances=20 \
  --region=${REGION}
```

## Updating the Service

### Deploy New Version

```bash
# Build new image
docker build -t gcr.io/${PROJECT_ID}/lifeos-task-orchestrator:v1.1.0 .
docker push gcr.io/${PROJECT_ID}/lifeos-task-orchestrator:v1.1.0

# Deploy with no downtime
gcloud run deploy lifeos-task-orchestrator \
  --image gcr.io/${PROJECT_ID}/lifeos-task-orchestrator:v1.1.0 \
  --region=${REGION}
```

### Rollback

```bash
# List revisions
gcloud run revisions list --service=lifeos-task-orchestrator --region=${REGION}

# Rollback to previous
gcloud run services update-traffic lifeos-task-orchestrator \
  --to-revisions=REVISION_NAME=100 \
  --region=${REGION}
```

## Security Best Practices

### 1. Authentication

Enable Cloud Run authentication:

```bash
gcloud run services update lifeos-task-orchestrator \
  --no-allow-unauthenticated \
  --region=${REGION}

# Create service account
gcloud iam service-accounts create lifeos-api-client

# Grant invoker role
gcloud run services add-iam-policy-binding lifeos-task-orchestrator \
  --member="serviceAccount:lifeos-api-client@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=${REGION}
```

### 2. Network Security

- Use VPC Connector for private database access
- Enable Cloud Armor for DDoS protection
- Use Cloud CDN for caching

### 3. Secrets Management

- Rotate secrets regularly
- Use Secret Manager versions
- Audit secret access

## Cost Optimization

### Current Costs (Estimates)

- **Cloud Run**: ~$25/month (1-10 instances)
- **Cloud SQL**: ~$15/month (db-f1-micro)
- **Pub/Sub**: ~$1/month (low volume)
- **Secret Manager**: <$1/month

**Total**: ~$40-50/month

### Optimization Tips

1. **Reduce Min Instances**: Set to 0 for non-production
2. **Use Smaller DB**: f1-micro is sufficient for testing
3. **Clean Up**: Delete unused resources
4. **Monitor Usage**: Set up billing alerts

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```bash
# Check Cloud SQL status
gcloud sql instances describe lifeos-db

# Verify connection string in secrets
gcloud secrets versions access latest --secret=database-url

# Test connection from Cloud Run
gcloud run services proxy lifeos-task-orchestrator --port=8080
```

#### 2. Image Pull Errors

```bash
# Verify image exists
gcloud container images list --repository=gcr.io/${PROJECT_ID}

# Check permissions
gcloud projects get-iam-policy ${PROJECT_ID}
```

#### 3. High Latency

- Check database query performance
- Review logs for slow operations
- Increase instance resources

### Logs

```bash
# Real-time logs
gcloud run services logs tail lifeos-task-orchestrator \
  --region=${REGION}

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit 20
```

## Cleanup

To delete all resources:

```bash
# Delete Cloud Run service
gcloud run services delete lifeos-task-orchestrator --region=${REGION}

# Delete Cloud SQL instance
gcloud sql instances delete lifeos-db

# Delete Pub/Sub topics
gcloud pubsub topics delete task-events
gcloud pubsub topics delete workflow-events

# Delete secrets
gcloud secrets delete database-url
gcloud secrets delete secret-key

# Delete images
gcloud container images delete gcr.io/${PROJECT_ID}/lifeos-task-orchestrator
```

## Next Steps

1. **Set up CI/CD**: GitHub Actions or Cloud Build
2. **Add Monitoring Dashboard**: Grafana or Cloud Monitoring
3. **Configure Backup**: Automated Cloud SQL backups
4. **Set up Staging Environment**: Separate project for testing
5. **Enable Cloud CDN**: For better performance
6. **Add Custom Domain**: Map custom domain to Cloud Run

## Support

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [GCP Support](https://cloud.google.com/support)

---

**Last Updated**: February 2026
