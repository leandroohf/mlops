# dags/sensor.py
import json
import os
import pendulum
from airflow.decorators import dag, task
from pendulum import datetime
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor,GCSObjectUpdateSensor

from google.cloud import storage
from google.oauth2 import service_account

from shared.dags_util import parse_gs_uri
from shared.datasets import MY_DATA

BUCKET, _ = parse_gs_uri(MY_DATA.uri)
OBJECT = "data/hello.txt"

FIXED_TS = pendulum.datetime(2025, 9, 20, 12, 57, 57, tz="America/Vancouver")

def fixed_ts(_context):
    return FIXED_TS  # must return a tz-aware datetime


@dag(
    start_date=datetime(2025, 1, 1),
    schedule=None,        # manual: trigger the DAG yourself
    catchup=False,
    description="Sensor hello world: wait for GCS file, then read and print",
    tags=["sensor", "gcs", "hello-world"],
)
def sensor_gcs_hello():


    print(f"Watching for gs://{BUCKET}/{OBJECT}")

    # NOTE: this use connections form Airflow to authenticate to GCP
    # 1) Wait (non-blocking) until the object exists in GCS
    # wait_for_file = GCSObjectExistenceSensor(
    #     task_id="wait_for_gcs_object",
    #     bucket=BUCKET,
    #     object=OBJECT,
    #     google_cloud_conn_id="google_cloud_default",
    #     poke_interval=5,        # seconds between checks
    #     timeout=60 * 60 * 12,    # give up after 12h
    #     mode="reschedule",       # don't hold a worker slot while waiting
    #     soft_fail=False,
    # )

    # 2) Optional: wait for file be updated
    wait_for_update = GCSObjectUpdateSensor(
        task_id="wait_for_gcs_object_update",
        bucket=BUCKET,
        object=OBJECT,
        google_cloud_conn_id="google_cloud_default",
        ts_func=fixed_ts,
        poke_interval=5,
        timeout=60 * 60 * 12,
        mode="reschedule",       # don't hold a worker slot while waiting
        deferrable=True,         # if your deployment has the Triggerer enabled
    )

    # 2) When present, read contents and print creation time
    @task(task_id="print_contents_and_creation")
    def read_and_print(bucket: str, blob_name: str):

        adc_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        with open(adc_path) as f:
            info = json.load(f)
        assert info.get("type") == "service_account", "Not a service-account keyfile."

        creds = service_account.Credentials.from_service_account_file(adc_path)
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        client = storage.Client(project=project, credentials=creds)
        blob = client.bucket(BUCKET).blob(OBJECT)


        # Sensor already guaranteed existence, but this is safe:
        if not blob.exists():
            raise RuntimeError(f"Blob gs://{BUCKET}/{OBJECT} not found!")

        text = blob.download_as_text()
        created = blob.time_created  # datetime
        print("=== GCS OBJECT ===")
        print(f"URI: gs://{BUCKET}/{OBJECT}")
        print(f"Created at: {created.isoformat() if created else 'unknown'}")
        print("Contents:")
        print(text)
        return {"uri": f"gs://{BUCKET}/{OBJECT}", "created": created.isoformat() if created else None}

    #wait_for_file >> read_and_print(BUCKET, OBJECT)
    wait_for_update >> read_and_print(BUCKET, OBJECT)

sensor_gcs_hello_dag = sensor_gcs_hello()

