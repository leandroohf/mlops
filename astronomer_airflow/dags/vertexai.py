import json
import os

from datetime import datetime, timedelta
from pyexpat import model
import pandas as pd

from airflow import DAG
from airflow.decorators import task
from airflow.models.baseoperator import chain

# Vertex AI (Google provider) – deferrable is supported in these operators
from airflow.providers.google.cloud.operators.vertex_ai.custom_job import (
    CreateCustomContainerTrainingJobOperator,
)

from google.cloud import storage
from google.oauth2 import service_account

from shared.dags_util import parse_gs_uri
from shared.datasets import MY_DATA

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("REGION")

# Public Vertex AI training image (any container works; we override command)
# You can also use gcr.io/cloud-marketplace/google/ubuntu2004 if you prefer.
TRAINING_IMAGE =  os.environ.get("TRAINING_IMAGE") 
STAGING_BUCKET = os.environ.get("STAGING_BUCKET")  # e.g. gs://my-bucket/staging

from io import BytesIO
import joblib

RUNTIME_ENVS = {
    # keep it to <=10 keys per Vertex AI limits
    "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT"),
    "REGION": os.environ.get("REGION"),
    "STAGING_BUCKET": os.environ.get("STAGING_BUCKET"),
    "TRAINING_IMAGE": os.environ.get("TRAINING_IMAGE"),
    "TRAINING_DATASET": os.environ.get("TRAINING_DATASET"),
    "MODEL_ARTIFACTS": os.environ.get("MODEL_ARTIFACTS"),
}


def load_model_artifacts_from_gcs(gcs_uri: str):
    # gcs_uri like: gs://my-bucket/path/to/model.pkl
    assert gcs_uri.startswith("gs://")

    bucket_name, object_name = parse_gs_uri(gcs_uri)

    adc_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    with open(adc_path) as f:
        info = json.load(f)
        assert info.get("type") == "service_account", "Not a service-account keyfile."

    creds = service_account.Credentials.from_service_account_file(adc_path)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = storage.Client(project=project, credentials=creds)
    blob = client.bucket(bucket_name).blob(object_name)

    model_bytes = blob.download_as_bytes()           # <-- in-memory bytes

    return joblib.load(BytesIO(model_bytes))         # returns your model


with DAG(
    dag_id="vertexai_train",
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
    
    print(f"PROJECT_ID: {PROJECT_ID}")
    print(f"REGION: {REGION}")
    print(f"Using training image: {TRAINING_IMAGE}")
    print(f"Using staging bucket: {STAGING_BUCKET}")

    # 1) Kick off a *fake* training job on Vertex AI.
    # deferrable=True => task defers to the Triggerer and wakes up only when the job finishes
    train = CreateCustomContainerTrainingJobOperator(
        task_id="vertex_fake_train",
        project_id=PROJECT_ID,
        region=REGION,
        display_name="fake-train-deferrable-demo",
        #container_uri="us-docker.pkg.dev/mlops-project-abacabb/bike-artifacts/train-image@sha256:223f77848d82766c5d0e7e5fbb849c48ca6d8faaed74838ce2ec187db1fc7ff3",
        container_uri=TRAINING_IMAGE,
        staging_bucket=STAGING_BUCKET,
        # NOTE: This command is run INSIDE the container on Vertex AI
        command=["python", "/app/train.py"],
        args=["--env=1.0.0"],   # NOTE: example of passing args to the training script. But inused this time
        # --- cost controls ---
        machine_type="e2-standard-4",   # small & cheap
        replica_count=1,                # single worker
        #accelerator_type=None,          # no GPU
        accelerator_count=0,
        # ----------------------
        # Turn on deferrable mode and set a poll cadence for the Trigger
        deferrable=True,
        poll_interval=60,  # seconds
        environment_variables=RUNTIME_ENVS,  # <-- inject runtime env here
    )

    # 2) Simple validation that runs only when Vertex AI job is completed successfully
    @task(task_id="validation")
    def validate():
        # In a real DAG, pull model_id or job info from XCom and verify artifacts/metrics.
        # This demo just prints success.
        print("Vertex AI job finished; running validation")

        model_artifact = os.environ.get("MODEL_ARTIFACTS")  # e.g. gs://my-bucket/model/model.pkl
        model = load_model_artifacts_from_gcs(model_artifact)

        print(f"Loaded dataset from: {model_artifact}")
        print(f"n_features_in_int_: {model.n_features_in_}")
        print(f"coef_: {model.coef_}")
        print(f"intercept_: {model.intercept_}")
        print(f"classes_: {model.classes_}")

    chain(train, validate())
