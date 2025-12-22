import json
import os
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, WorkerOptions

PROJECT_ID = os.getenv('PROJECT_ID', '')
PUBSUB_TOPIC = os.getenv('PUBSUB_TOPIC', '')
SUBSCRIPTION_NAME = os.getenv('SUBSCRIPTION', '')

RAW_EVENT_TABLE = os.getenv('RAW_EVENT_TABLE', '')

BUCKET_NAME = os.getenv('BUCKET_NAME', '')

DATAFLOW_SERVICE_ACCOUNT = os.getenv('SA', '')
JOB_NAME = os.getenv("INJECT_SENSOR_DATA_JOB_NAME")

print(f"PROJECT_ID={PROJECT_ID}, PUBSUB_TOPIC={PUBSUB_TOPIC}, RAW_EVENT_TABLE={RAW_EVENT_TABLE}, JOB_NAME={JOB_NAME}")

def print_debug_element(row):
    print("[DEBUG] Element Type:", type(row))
    print("[DEBUG] Element Content:", row)
    return row

class ParsePubSubMessage(beam.DoFn):

    # NOTE: process each json message
    def process(self, message):
        record = json.loads(message.decode('utf-8'))
        yield {
            "event_id": record["event_id"],
            "station_id": record["station_id"],
            "ts_iso": record["ts_iso"],
            "kind": record["kind"],
            "delta": int(record["delta"]),
            "event_date": record["event_date"]
        }

def launch_stream_pipeline():

    # NOTE: defines apache beam pipe options where to run it (google cloud dataflow)
    options = PipelineOptions(
        streaming=True,
        project=PROJECT_ID,
        region='us-central1',  # or your region
        runner='DataflowRunner', # NOTE: this mean run on google cloud dataflow
        temp_location=f'{BUCKET_NAME}/bike_stream/tmp/',
        staging_location=f'{BUCKET_NAME}/bike_stream/staging/',
        #service_account_email=DATAFLOW_SERVICE_ACCOUNT,
        job_name=JOB_NAME
    )

    # NOTE: Set streaming explicitly
    options.view_as(StandardOptions).streaming = True

    # NOTE: Set worker configuration
    worker_options = options.view_as(WorkerOptions)
    worker_options.num_workers = 1
    worker_options.max_num_workers = 1
    worker_options.machine_type = 'n1-standard-1'

    # NOTE: Define the Beam pipeline steps
    with beam.Pipeline(options=options) as p:
        (
            p
            # NOTE: read from pubsub (source)
            # outputs a PCollection of messages (byte strings)
            # Ex: b'{"event_id": "e-90001", "station_id": "A_205", "ts_iso": "2025-12-08T00:04:47+00:00", "kind": "pickup", "delta": 1}'
            | 'ReadFromPubSub' >> beam.io.ReadFromPubSub(subscription=SUBSCRIPTION_NAME)
            # NOTE: run the code defined in ParsePubSubMessage.process() (transform)
            # outputs a PCollection of dicts (Dict[str, Any]). Ex:
            # {
            # 'event_id': 'e-90001',
            # 'station_id': 'A_205',
            # 'ts_iso': '2025-12-08T00:04:47+00:00',
            # 'kind': 'pickup',
            # 'delta': 1
            # 'event_date': '2025-12-08'
            # }
            | 'ParseJSON' >> beam.ParDo(ParsePubSubMessage())
            | 'DebugPrint' >> beam.Map(lambda row: print_debug_element(row))
            # NOTE: write in table with schema (sink = store)
            | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
                table=RAW_EVENT_TABLE,
                schema={
                    'fields': [
                        {'name': 'event_id', 'type': 'STRING', 'mode': 'REQUIRED'},
                        {'name': 'station_id', 'type': 'STRING', 'mode': 'REQUIRED'},
                        {'name': 'ts_iso', 'type': 'STRING', 'mode': 'REQUIRED'},
                        {'name': 'kind', 'type': 'STRING', 'mode': 'REQUIRED'},
                        {'name': 'delta', 'type': 'INTEGER', 'mode': 'REQUIRED'},
                        {'name': 'event_date', 'type': 'STRING', 'mode': 'REQUIRED'},
                    ]
                },
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
            )
        )

if __name__ == '__main__':

    # NOTE: what happen here
    # 1) GCP authenticates and sets up the Dataflow job
    # 2) Code is uploaded to staging bucket
    # 3) Dataflow streaming job is launched (lazily initialized)
    #    3.1) The code is only ran when the first message arrives in Pub/Sub 
    # 4) It starts pulling Pub/Sub messages and each message is parsed and inserted into BigQuery
    launch_stream_pipeline()
