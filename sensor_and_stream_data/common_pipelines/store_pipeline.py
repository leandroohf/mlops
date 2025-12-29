import json
import os
import sys

import apache_beam as beam
from apache_beam.pvalue import PCollection

from typing import Dict, Any, List

import logging
log_level = os.getenv("LOG_LEVEL", "INFO")


FEATURES_TABLE = os.getenv('FEATURES_TABLE', '')

class LogAndFlushFn(beam.DoFn):
    def __init__(self, run_ts: str):
        self.run_ts = run_ts

    def process(self, count):
        logging.info(f"Raw events read at {self.run_ts} (UTC): {count or 0}")
        sys.stdout.flush()
        yield count

class RunMergeFn(beam.DoFn):

    def __init__(self, feature_table):
        self.feature_table = feature_table

    def process(self, elements: List[Dict[str, Any]]):
        from google.cloud import bigquery
        import uuid

        # NOTE: Input example:
        # elements = [
        #     {'station_id': 'A_101', 'feature_name': 'pickup_count', 'value': 5, ...},
        #     {'station_id': 'A_101', 'feature_name': 'dropoff_count', 'value': 2, ...},
        #     {'station_id': 'A_205', 'feature_name': 'pickup_count', 'value': 3, ...},
        # ]

        client = bigquery.Client()

        # Create temporary table name
        temp_table = self.feature_table + "_temp_" + uuid.uuid4().hex[:8]

        # NOTE: Upload batched features from json to temp table
        load_job = client.load_table_from_json(elements, temp_table)
        # NOTE: Blocks execution until the load job finishes (either success or failure).
        load_job.result()

        logging.info(f"Job ID: {load_job.job_id}")
        logging.info(f"Job State: {load_job.state}")
        logging.info(f"Output rows: {load_job.output_rows}")
        logging.info(f"Expected input size: {len(elements)}")
        logging.info(f"Creating temporary table: {temp_table}")

        # NOTE: Updates (Upsert) features table from temp table
        merge_sql = f"""
        MERGE `{self.feature_table}` T
        USING `{temp_table}` S
        ON T.station_id = S.station_id AND
            T.feature_name = S.feature_name AND
            T.window_len = S.window_len AND
            T.as_of = S.as_of
        WHEN MATCHED THEN
            UPDATE SET value = S.value
        WHEN NOT MATCHED THEN
            INSERT (station_id, feature_name, window_len, value, as_of)
            VALUES (S.station_id, S.feature_name, S.window_len, S.value, S.as_of)
        """
        # client.query(merge_sql).result()
        merge_job = client.query(merge_sql)
        # NOTE: wait/block until the job finishes (required)
        merge_job.result() # <= blocks until done

        # NOTE: Access number of affected rows (inserted + updated)
        affected_rows = merge_job.num_dml_affected_rows
        logging.info(f"Merge Job ID: {merge_job.job_id}")
        logging.info(f"Number of affected rows by MERGE: {affected_rows}")

        logging.info(f"Temporary table {temp_table} merged into {self.feature_table}. Deleting temp table...")
        client.delete_table(temp_table, not_found_ok=True)

        logging.info(f"MERGE completed from {temp_table} to {self.feature_table}")
        sys.stdout.flush()

        yield "merge_success"

def get_store_pipeline(grouped: PCollection[List[Dict[str, Any]]],
                        runner: str) -> PCollection:
    
    assert runner in {"test", "DirectRunner", "DataflowRunner"}, f"Unsupported runner: {runner}"

    def _write_local(pcoll: PCollection) -> PCollection:
        # NOTE: Save locally for inspection
        return (
            pcoll
            | "SerializeLocal" >> beam.Map(json.dumps)
            | "SaveLocal" >> beam.io.WriteToText(
                "data/features",
                file_name_suffix=".json",
                num_shards=1,
                shard_name_template="",
                coder=beam.coders.StrUtf8Coder(),
            )
        )

    def _write_bq(pcoll: PCollection) -> PCollection:

        # NOTE: Log number of feature records processed
        # _ = (
        #     pcoll
        #     | "CountFeaturesUpserted" >> beam.combiners.Count.Globally()
        #     | "LogFeatureUpserts" >> beam.Map(lambda count: logging.info(f"Features upserted: {count}"))
        # )

        # NOTE: Run MERGE for each batch and update feature table in BigQuery
        return pcoll | "RunMERGE" >> beam.ParDo(RunMergeFn(FEATURES_TABLE))

    if runner == "test":
        # NOTE: 1) test -> local only
        return _write_local(grouped)

    if runner == "DirectRunner":
        # NOTE: 2) DirectRunner -> local + BQ (branch, return one of them)
        _ = _write_local(grouped)
        return _write_bq(grouped)

    # NOTE: 3) DataflowRunner -> BQ only
    return _write_bq(grouped)

