
# NOTE: cloud function gen1 require context arg
def pubsub_to_bq(event, context):
    import base64
    import json
    import os
    from google.cloud import bigquery

    client = bigquery.Client()
    RAW_EVENT_TABLE = os.getenv("RAW_EVENT_TABLE", None)

    assert RAW_EVENT_TABLE is not None, "RAW_EVENT_TABLE environment variable must be set"

    data = base64.b64decode(event['data']).decode('utf-8')
    payload = json.loads(data)

    row = {
        "event_id": payload["event_id"],
        "station_id": payload["station_id"],
        "ts_iso": payload["ts_iso"],
        "kind": payload["kind"],
        "delta": int(payload["delta"])
    }

    errors = client.insert_rows_json(RAW_EVENT_TABLE, [row])
    if errors:
        print("BQ insert error:", errors)
