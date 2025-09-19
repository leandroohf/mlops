from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.decorators import task
from airflow.models.baseoperator import chain

# Vertex AI (Google provider) – deferrable is supported in these operators
from airflow.providers.google.cloud.operators.vertex_ai.custom_job import (
    CreateCustomContainerTrainingJobOperator,
)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("REGION")

# Public Vertex AI training image (any container works; we override command)
# You can also use gcr.io/cloud-marketplace/google/ubuntu2004 if you prefer.
TRAINING_IMAGE =  os.environ.get("TRAINING_IMAGE_CHECK") 
STAGING_BUCKET = os.environ.get("STAGING_BUCKET")  # e.g. gs://my-bucket/staging

with DAG(
    dag_id="vertexai_check_deferrable",
    start_date=datetime(2025, 1, 1),
    schedule=None,                # trigger on demand
    catchup=False,
    default_args={
        "owner": "data-platform",
        "retries": 0,
    },
    dagrun_timeout=timedelta(hours=2),
    tags=["vertexai", "deferrable", "demo"],
) as dag:

    # 1) Kick off a *fake* training job on Vertex AI.
    # deferrable=True => task defers to the Triggerer and wakes up only when the job finishes
    train = CreateCustomContainerTrainingJobOperator(
        task_id="vertex_simple_train",
        project_id=PROJECT_ID,
        region=REGION,
        display_name="fake-simple-training-for-check",
        container_uri=TRAINING_IMAGE,
        staging_bucket=STAGING_BUCKET,
        # This command is run INSIDE the container on Vertex AI
        command=[
            "bash",
            "-lc",
            # Simulate a short train, write an artifact, then exit 0
            'echo "Starting fake train..."; '
            "python - <<'PY'\n"
            "import time, json, pathlib\n"
            "print('Training...'); time.sleep(20)\n"
            "pathlib.Path('/gcs').mkdir(exist_ok=True)\n"
            "print(json.dumps({'status':'ok','metric':0.987}))\n"
            "PY\n"
            'echo "Done."\n'
        ],
        # --- cost controls ---
        machine_type="e2-standard-4",   # small & cheap
        replica_count=1,                # single worker
        #accelerator_type=None,          # no GPU
        accelerator_count=0,
        # ----------------------
        # Turn on deferrable mode and set a poll cadence for the Trigger
        deferrable=True,
        poll_interval=60,  # seconds
    )

    # 2) Simple validation that runs only when Vertex AI job is completed successfully
    @task(task_id="validation")
    def validate():
        # In a real DAG, pull model_id or job info from XCom and verify artifacts/metrics.
        # This demo just prints success.
        print("Vertex AI job finished; running validation")

    chain(train, validate())
