
from datetime import datetime
import json
import os
import sys
import apache_beam as beam

RAW_EVENT_TABLE = os.getenv('RAW_EVENT_TABLE', '')

import logging
log_level = os.getenv("LOG_LEVEL", "INFO")

from datetime import timezone


class LogAndFlushFn(beam.DoFn):
    def __init__(self, run_ts: str):
        self.run_ts = run_ts

    def process(self, count):
        logging.info(f"Raw events read at {self.run_ts} (UTC): {count or 0}")
        sys.stdout.flush()
        yield count

def _to_event_timestamp(ts):

    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.timestamp()

    raise TypeError(f"Unsupported ts_iso type: {type(ts)}")

def _debug_write_csv(raw_events: beam.PCollection, path_prefix: str) -> None:
    """Write a quick CSV-like debug file. Leaves raw_events unchanged."""
    _ = (
        raw_events
        | "DebugToCSVLine" >> beam.Map(
            lambda r: ",".join(str(r.get(k, "")) for k in sorted(r.keys()))
        )
        | "WriteLocalCSV" >> beam.io.WriteToText(
            path_prefix,
            file_name_suffix=".csv",
            num_shards=1,
        )
    )

def _add_event_timestamps(raw_events: beam.PCollection) -> beam.PCollection:
    """Attach event-time timestamp to each row (dict preserved)."""
    return raw_events | "AddTimestamps" >> beam.Map(
        lambda row: beam.window.TimestampedValue(
            row,
            _to_event_timestamp(row["ts_iso"]),
        )
    )


def get_load_pipeline(p: beam.Pipeline, runner: str) ->  beam.PCollection:

    assert runner in {"DirectRunner", "DataflowRunner", "test"}, f"Unsupported runner: {runner}"

    if runner == "test":
        # NOTE: for testing purposes only: read from local json file
        raw_events = (
            p
            | "ReadLocalEvents" >> beam.io.ReadFromText("data/sample_data.json")
            | "ParseJSON" >> beam.Map(json.loads)   # -> dict per line
        )
    else:
        # NOTE: Read raw events from BigQuery (limited to today's partition)
        raw_events = (
            p
            | "ReadRawEvents" >> beam.io.ReadFromBigQuery(
                query=f"""
                    SELECT * FROM  `{RAW_EVENT_TABLE}`
                    WHERE event_date = CURRENT_DATE()
                """,
                use_standard_sql=True,
            )
        )

    # NOTE: local data debugging
    if runner in {"DirectRunner", "test"}:
        _debug_write_csv(raw_events, "data/raw_events_debug" )

    # NOTE: add event-time timestamps (dicts preserved) Always add timestamps
    raw_events = _add_event_timestamps(raw_events)

    # NOTE: Log number of raw events (prod safe)
    # if PCollection is empty, count will be None
    run_ts = datetime.utcnow().replace(microsecond=0).isoformat()
    _ = (
        raw_events
        | "CountRawEvents" >> beam.combiners.Count.Globally()
        | "LogRawEventsCount" >> beam.ParDo(LogAndFlushFn(run_ts))
    )
    return raw_events