import os

QUERY = None  # Global cache


def load_query_template():
    RAW_EVENT_TABLE = os.getenv("RAW_EVENT_TABLE", None)
    FEATURE_EVENT_TABLE = os.getenv("FEATURE_EVENT_TABLE", None)

    assert RAW_EVENT_TABLE and FEATURE_EVENT_TABLE, "Missing required environment variable(s)."

    query_path = os.path.join(os.path.dirname(__file__), "upsert_station_features.sql")

    with open(query_path, "r") as f:
        query = f.read()

    print("Using RAW_EVENT_TABLE:", RAW_EVENT_TABLE)
    print("Using FEATURE_EVENT_TABLE:", FEATURE_EVENT_TABLE)

    query = query.replace("${RAW_EVENT_TABLE}", RAW_EVENT_TABLE)
    query = query.replace("${FEATURE_EVENT_TABLE}", FEATURE_EVENT_TABLE)

    return query


def compute_and_upsert_features(request):
    from google.cloud import bigquery
    from datetime import datetime, timezone

    global QUERY
    if QUERY is None:
        QUERY = load_query_template()

    now = datetime.now(timezone.utc)
    print("Running feature upsert at:", now.isoformat())

    client = bigquery.Client()
    job = client.query(QUERY)
    job.result()

    return {"status": "ok"}
