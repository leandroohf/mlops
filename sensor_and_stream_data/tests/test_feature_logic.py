# tests/test_feature_logic.py

import datetime
from typing import Dict, Any, List
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from common_pipelines.feature_engineer_pipeline import build_features_pipeline

from loguru import logger


FAKE_EVENTS = [
    {
        "event_id": "e-1",
        "station_id": "A_101",
        "ts_iso": datetime.datetime(2025, 12, 8, 10, 0, 0),
        "kind": "pickup",
        "delta": 1,
    },
    {
        "event_id": "e-2",
        "station_id": "A_101",
        "ts_iso": datetime.datetime(2025, 12, 8, 10, 10, 0),
        "kind": "pickup",
        "delta": 1,
    },
    {
        "event_id": "e-3",
        "station_id": "A_102",
        "ts_iso": datetime.datetime(2025, 12, 8, 10, 40, 0),
        "kind": "dropoff",
        "delta": 1,
    },
]


class MockRunMergeFn(beam.DoFn):
    def process(self, elements: List[Dict[str, Any]]):
        logger.debug("--- MOCK MERGE OUTPUT ---")
        for row in elements:
            logger.debug(row)
        logger.debug("--- END ---")
        yield elements


def add_timestamp(row: Dict[str, Any]):
    ts = row["ts_iso"].timestamp()
    logger.debug(f"Assigning timestamp {ts} to row: {row}")
    return beam.window.TimestampedValue(row, ts)


def debug_pickup_format(row: Dict[str, Any]) -> Dict[str, Any]:
    logger.debug(f"Formatted pickup row: {row}")
    return row


def test_locally():

    logger.info("Starting local test of feature engineering pipeline")

    options = PipelineOptions(runner="DirectRunner")

    with beam.Pipeline(options=options) as p:

        # NOTE: Mock raw events table
        raw_events = (
            p
            | "CreateFakeEvents" >> beam.Create(FAKE_EVENTS)
            | "AddTimestamps" >> beam.Map(add_timestamp)
        )

        grouped = build_features_pipeline(p, raw_events)

        grouped | "MockMERGE" >> beam.ParDo(MockRunMergeFn())


if __name__ == "__main__":
    test_locally()
