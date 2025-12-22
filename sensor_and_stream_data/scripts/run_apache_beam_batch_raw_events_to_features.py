from datetime import datetime, timezone
import json
import os
import sys
from typing import Optional
import uuid

import typer

import logging

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, WorkerOptions

from common_pipelines.feature_engineer_pipeline import build_features_pipeline
from common_pipelines.load_pipeline import get_load_pipeline
from common_pipelines.store_pipeline import get_store_pipeline

# NOTE: export LOG_LEVEL=DEBUG  <== for debug messages  (default is INFO)
log_level = os.getenv("LOG_LEVEL", "INFO")

# Set up the logger
# logger.remove()  # Remove any previously added sinks
# logger.add(sys.stdout, level=log_level)


app = typer.Typer()


PROJECT_ID = os.getenv('PROJECT_ID', '')

RAW_EVENT_TABLE = os.getenv('RAW_EVENT_TABLE', '')
FEATURES_TABLE = os.getenv('FEATURES_TABLE', '')
BUCKET = os.getenv('BUCKET', '')

assert 'gs://' in BUCKET, "BUCKET must be a GCS path starting with 'gs://'"

DATAFLOW_SERVICE_ACCOUNT = os.getenv('SA', '')
FEATURE_JOB_NAME = os.getenv("FEATURE_ENGINEERING_JOB_NAME")

def run_features_engineering_pipeline(run_ts: str, runner="DirectRunner"):

    uid = uuid.uuid4().hex[:6]
    GCS_OUTPUT_PATH = f"{BUCKET}/run/{run_ts}_{uid}/features"

    assert runner in {"DirectRunner", "DataflowRunner", "test"}, "Invalid runner. Use 'DirectRunner', 'test', or 'DataflowRunner'"

    logging.info(f"GCS_OUTPUT_PATH: {GCS_OUTPUT_PATH}")

    runner_engine = "DirectRunner" if runner in ["DirectRunner", "test"] else "DataflowRunner"

    # NOTE: defines apache beam pipe options where to run it (google cloud dataflow)
    options = PipelineOptions(
        streaming=True,
        project=PROJECT_ID,
        region='us-central1',  # or your region
        runner=runner_engine, # NOTE: this mean run on google cloud dataflow
        temp_location=f'{BUCKET}/bike_stream/tmp/',
        staging_location=f'{BUCKET}/bike_stream/staging/',
        service_account_email=DATAFLOW_SERVICE_ACCOUNT,
        job_name=FEATURE_JOB_NAME,
        setup_file="./setup.py"
    )

    # NOTE: Set bounded source explicitly (This is not a streaming job)
    options.view_as(StandardOptions).streaming = False

    # NOTE: Set worker configuration
    worker_options = options.view_as(WorkerOptions)
    worker_options.num_workers = 1
    worker_options.max_num_workers = 1
    worker_options.machine_type = 'n1-standard-1'

    # NOTE: Define the Beam pipeline steps
    # This apache beam pipeline sources is BigQuery (bounded source) and not a stream source like PubSub used in
    # insertion data beam pipeline
    with beam.Pipeline(options=options) as p:

        raw_events = get_load_pipeline(p, runner)

        grouped = build_features_pipeline(p, raw_events)

        if runner == "DataflowRunner":
            # NOTE: save features into bucket for debugging and auditing (considered good pactices)
            _ = (
                grouped
                | "SerializeToJSON" >> beam.Map(json.dumps)
                | "SaveToGCS" >> beam.io.WriteToText(
                    GCS_OUTPUT_PATH,
                    file_name_suffix=".json",
                    num_shards=1,
                    shard_name_template="",
                    coder=beam.coders.StrUtf8Coder()
                )
            )

        _ = get_store_pipeline(
            grouped,
            runner=runner
        )


@app.command()
def main(
    run_timestamp: Optional[str] = typer.Option(
        None,
        help="UTC timestamp. Example: '2025-12-13T16:00:00Z'"
    ),
    runner: str = typer.Option(
        "DirectRunner",
        help="Apache Beam runner. Use 'DirectRunner' or 'test' for local runs, 'DataflowRunner' for GCP."
    )
):
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # NOTE: what happen here
    # 1) GCP authenticates and sets up the Dataflow job
    # 2) Code is uploaded to staging bucket
    typer.echo(f"Running with timestamp: {run_timestamp}")
    typer.echo(f"Using runner: {runner}")
    run_features_engineering_pipeline(run_timestamp, runner=runner)

if __name__ == '__main__':
    app()

"""
CLI: how to run locally but reading from test json file
python scripts/run_apache_beam_batch_raw_events_to_features.py \
 --runner=test --run-timestamp=2025-12-13
"""

"""
CLI: how to run locally
python scripts/run_apache_beam_batch_raw_events_to_features.py
"""

"""
CLI: how to run on cloud dataflow
python scripts/run_apache_beam_batch_raw_events_to_features.py \
  --runner=DataflowRunner \
  --run-timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
"""
