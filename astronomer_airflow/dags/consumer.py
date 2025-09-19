import json
import os

import pandas as pd
from airflow.decorators import dag, task
from pendulum import datetime

from google.cloud import storage
from google.oauth2 import service_account

# shared 
from shared.dags_util import parse_gs_uri
from shared.datasets import MY_DATA


# NOTE: this dag belongs to Data Scientist team
@dag(
    start_date=datetime(2023, 1, 1),
    schedule=[MY_DATA],  # this DAG triggers when dataset is updated
    catchup=False,
    description="DAG that consumes data"
)
def consumer_dag():
    @task
    def train_model():

        print("Training model with new dataset")

        gcs_uri = MY_DATA.uri

        assert MY_DATA.uri.startswith("gs://")
       
        bucket_name, object_name = parse_gs_uri(MY_DATA.uri)

        adc_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        with open(adc_path) as f:
            info = json.load(f)
        assert info.get("type") == "service_account", "Not a service-account keyfile."

        creds = service_account.Credentials.from_service_account_file(adc_path)
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        client = storage.Client(project=project, credentials=creds)
        blob = client.bucket(bucket_name).blob(object_name)
    
        with blob.open("rb") as f:     # 'rb' works for CSV and avoids loading everything twice
            training_data = pd.read_csv(f)

        print(f"Loaded dataset from: {gcs_uri}")
        print(f"DataFrame shape: {training_data.shape}")
        print(f"Columns: {list(training_data.columns)}")

    train_model()

consumer_dag = consumer_dag()

