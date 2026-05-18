#!/bin/bash
set -euo pipefail

# Read config from config.yaml
PROJECT_ID=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['gcp_project'])")
REGION=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['gcp_region'])")
SECRET_NAME=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['secret_name'])")
TOPIC=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['topic'])")
SCHEDULE=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['schedule'])")
TIMEZONE=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['timezone'])")
JOB_NAME=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yaml'))['scheduler_job'])")

echo "Deploying to project: $PROJECT_ID, region: $REGION"

# Copy config.yaml into each function's source directory
cp config.yaml functions/generate_report/config.yaml
cp config.yaml functions/api/config.yaml

# Create Pub/Sub topic (idempotent)
gcloud pubsub topics create "$TOPIC" --project="$PROJECT_ID" 2>/dev/null || true

# Deploy generate_report function
echo "Deploying generate-report function..."
gcloud functions deploy generate-report \
    --gen2 \
    --runtime=python312 \
    --region="$REGION" \
    --source=functions/generate_report \
    --entry-point=generate_report \
    --trigger-topic="$TOPIC" \
    --timeout=540s \
    --memory=1Gi \
    --set-secrets="/etc/secrets/.env=$SECRET_NAME:latest" \
    --project="$PROJECT_ID"

# Cloud Functions caps event-triggered timeout at 540s, but Cloud Run allows 3600s
echo "Extending Cloud Run timeout to 3600s..."
gcloud run services update generate-report \
    --timeout=3600 \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --quiet

# Deploy API function
echo "Deploying api function..."
gcloud functions deploy api \
    --gen2 \
    --runtime=python312 \
    --region="$REGION" \
    --source=functions/api \
    --entry-point=api \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=60s \
    --memory=256Mi \
    --set-secrets="/etc/secrets/.env=$SECRET_NAME:latest" \
    --project="$PROJECT_ID"

# Clean up copied config files
rm -f functions/generate_report/config.yaml functions/api/config.yaml

# Create/update Cloud Scheduler job
echo "Configuring Cloud Scheduler..."
gcloud scheduler jobs delete "$JOB_NAME" \
    --location="$REGION" --project="$PROJECT_ID" --quiet 2>/dev/null || true
gcloud scheduler jobs create pubsub "$JOB_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --time-zone="$TIMEZONE" \
    --topic="projects/$PROJECT_ID/topics/$TOPIC" \
    --message-body='{}' \
    --project="$PROJECT_ID"

API_URL="https://$REGION-$PROJECT_ID.cloudfunctions.net/api"
echo ""
echo "Deployment complete!"
echo "API: $API_URL"
