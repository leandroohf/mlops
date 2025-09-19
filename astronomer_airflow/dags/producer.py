import json
import os

import pendulum
from airflow.decorators import dag, task
from pendulum import datetime
import pandas as pd

from google.cloud import storage
from google.oauth2 import service_account

# shared Dataset
from shared.dags_util import parse_gs_uri
from shared.datasets import MY_DATA


# NOTE: this dag belongs to Data engineering team
@dag(
    start_date=datetime(2023, 1, 1),
    schedule="@daily",
    catchup=False,
    description="DAG that produces data"
)
def producer_dag():
    @task(outlets=[MY_DATA])  # this task updates the dataset
    def produce_data():
        # NOTE: write the data in this file
        # when returned signs airflow intrenally db that the dataset
        # were updated and then airflow tirgger the consumer dag
       
        print(f"Writing new data to {MY_DATA.uri}")

        assert MY_DATA.uri.startswith("gs://")
       
        bucket_name, object_name = parse_gs_uri(MY_DATA.uri)

        print(f"bucket name: {bucket_name}, object name: {object_name}")

        #text = f"hello world: {datetime.now()}"

        ts = pendulum.now("UTC").to_iso8601_string()
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "label": ["alpha", "beta", "gamma"],
                "created_at": [ts, ts, ts],
            }
        )

        csv_text = df.to_csv(index=False)

        adc_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        with open(adc_path) as f:
            info = json.load(f)
        assert info.get("type") == "service_account", "Not a service-account keyfile."

        creds = service_account.Credentials.from_service_account_file(adc_path)
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")

        # Use the project from the SA file
        # client = storage.Client(project=creds.project_id, credentials=creds)
        client = storage.Client(project=project, credentials=creds)

        #client = storage.Client()  # uses ADC
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        #blob.upload_from_string(text, content_type="text/plain")
        blob.upload_from_string(csv_text, content_type="text/csv")

        gcs_uri = MY_DATA.uri

        return gcs_uri

    produce_data()

producer_dag = producer_dag()

