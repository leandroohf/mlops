#!/bin/bash
set -euo pipefail

# NOTE: How to set glcloud acccount
# list accounts: gcloud auth list
# change account: gcloud config set account your_email@gmail.com
# list billing account: gcloud billing accounts list
# list all projects: gcgcloud projects list

CONFIG_PATH="common/config.yaml"

prompt_step() {
  local question="$1"

  echo
  read -p "$question? [c]ontinue / [s]kip / [a]bort: " reply
  case "$reply" in
    [Cc]*) return 0 ;;  # Continue
    [Ss]*) echo "  Skipping: $question"; return 1 ;;  # Skip
    *) echo "  Aborted by user."; exit 1 ;;  # Abort
  esac
}


check_gcloud_account() {
  echo "Fetching authenticated gcloud accounts..."
  echo

  gcloud auth list

  active_account=$(gcloud config get-value account 2>/dev/null)

  echo
  echo "Active account: $active_account"
  echo

  read -p "Do you want to continue with this account? (y/n): " confirm

  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "Continuing with account: $active_account"
  else
    echo "Exiting. You can change the account using:"
    echo "  gcloud auth login"
    return 1
  fi
}

load_config() {
  
  PROJECT_NAME=$(yq '.project_name' "$CONFIG_PATH")
  PROJECT_ID=$(yq '.project_id' "$CONFIG_PATH")
  REGION=$(yq '.region' "$CONFIG_PATH")
  BUCKET_NAME=$(yq '.bucket_name' "$CONFIG_PATH")
  DOCKER_REGISTRY_NAME=$(yq '.docker_registry_name' "$CONFIG_PATH")
  DOCKER_IMAGE==$(yq '.docker_image' "$CONFIG_PATH")
  CLOUD_RUN_JOB_NAME=$(yq '.cloud_run_job_name' "$CONFIG_PATH")
  CLOUD_RUN_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${DOCKER_REGISTRY_NAME}/${DOCKER_IMAGE}:latest"

  echo
  echo "  Loaded Configuration:"
  echo "------------------------"
  echo "Project Name         : $PROJECT_NAME"
  echo "Project ID           : $PROJECT_ID"
  echo "Region               : $REGION"
  echo "Docker Registry Name : $DOCKER_REGISTRY_NAME"
  echo "GCS Bucket Name      : $BUCKET_NAME"
  echo "Cloud Run Job Name   : $CLOUD_RUN_JOB_NAME"
  echo "Cloud Run Image      : $CLOUD_RUN_IMAGE"
  echo "------------------------"
  echo

  read -p "Continue with this configuration? (y/n): " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted by user."
    exit 1
  fi
}

create_gcp_project() {

  # NOTE: Prompt silently if BILLING_ACCOUNT_ID is not set or empty
  if [[ -z "${BILLING_ACCOUNT_ID:-}" ]]; then
    echo -n "Enter your Billing Account ID (format: XXXXXX-XXXXXX-XXXXXX): "
    read -s BILLING_ACCOUNT_ID
    echo  # newline after silent input
  fi

  echo "Creating project: $PROJECT_NAME ($PROJECT_ID)"
  gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"

  echo "Linking billing account..."
  gcloud beta billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"

  echo "Setting as active project..."
  gcloud config set project "$PROJECT_ID"

  echo "Enabling required APIs..."
  gcloud services enable run.googleapis.com \
      storage.googleapis.com \
      artifactregistry.googleapis.com

  echo "Project setup complete."
}

check_if_project_exists() {
  echo "Checking if project '$PROJECT_ID' exists..."

  if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    echo "Project '$PROJECT_ID' already exists."
    return 0
  else
    echo "Project '$PROJECT_ID' does not exist."
    return 1
  fi
}

create_gcs_bucket() {

  echo "Creating GCS bucket: $BUCKET_NAME"
  gcloud storage buckets create "gs://$BUCKET_NAME" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    || echo "GCS bucket may already exist."
}

create_artifact_registry() {

  echo "Creating Artifact Registry: $DOCKER_REGISTRY_NAME"
  gcloud artifacts repositories create "$DOCKER_REGISTRY_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Docker registry for ML pipeline images" \
    || echo "Artifact Registry may already exist."
}

create_cloud_run_job() {
  echo "Creating Cloud Run Job: $CLOUD_RUN_JOB_NAME"
  gcloud run jobs create "$CLOUD_RUN_JOB_NAME" \
    --image="$CLOUD_RUN_IMAGE" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --command="python" \
    --args="main.py" \
    || echo "Cloud Run job may already exist."
}

main() {

  # 0. check current cloud accunt
  check_gcloud_account

  # 1. load config
  echo "Loading configuration from $CONFIG_PATH"
  load_config
  
  # 2. create project
  # TODO: add prompt asking if wann continue/abort/skip and adjust code
  if prompt_step "Step 2: Create GCP project"; then
    create_gcp_project
  fi
  check_if_project_exists

  # 3. create gcs (one-time):
   if prompt_step "Step 3: Create GCS bucket"; then
    create_gcs_bucket
  fi

  # 4. create docker registry (one-time):
  if prompt_step "Step 4: Create Docker registry"; then
    create_artifact_registry
  fi
  
  # 5. Create the Cloud Run Job (one-time):
  if prompt_step "Step 5: Create Cloud Run Job"; then
    create_cloud_run_job
  fi
  
  echo "Setup complete!"
}

main




