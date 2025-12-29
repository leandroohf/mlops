import json
import os
import time
import random
from datetime import datetime, timezone

from google.cloud import pubsub_v1


CITY_ID = "C_001"
STATIONS = ["A_101", "A_205", "A_310"]
KINDS = ["pickup", "dropoff"]

PROJECT_ID = os.getenv("PROJECT_ID")
TOPIC_ID = os.getenv("PUBSUB_TOPIC")

print(f"Using PROJECT_ID='{PROJECT_ID}' and TOPIC_ID='{TOPIC_ID}'\n\n")

publisher = pubsub_v1.PublisherClient()
topic_path = TOPIC_ID# publisher.topic_path(PROJECT_ID, TOPIC_ID)

def generate_event(event_counter: int) -> dict:

    station_id = random.choice(STATIONS)
    kind = random.choice(KINDS)
    ts_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')
    delta = +1  # fixed in your example; could randomize or alternate if needed
    event_id = f"e-{90000 + event_counter:05d}"

    event_date = datetime.now(timezone.utc).date().isoformat()

    return {
        "event_id": event_id,
        "station_id": station_id,
        "city_id": CITY_ID,
        "ts_iso": ts_iso,
        "kind": kind,
        "delta": delta,
        "event_date": event_date
    }

def publish_event(event_data: dict):

    # NOTE: why future? It represents a promise of a result in the future
    # the actual publish result isn’t immediately available
    # The operation is atomic from the client’s perspective

    # NOTE: encode as bytes
    # message = str(event_data).encode("utf-8")
    # future = publisher.publish(topic_path, message)

    # NOTE: encode as JSON
    message_json = json.dumps(event_data)
    message_bytes = message_json.encode("utf-8")
    future = publisher.publish(topic_path, message_bytes)


    print(f"Published: {event_data}")
    return future.result()


def simulate_sensors(n_events: int = 5, delay_seconds: float = 1.0) -> None:

    for i in range(n_events):
        event = generate_event(i + 1)
        #print(event)
        publish_event(event)
        time.sleep(delay_seconds)


if __name__ == "__main__":
    simulate_sensors(n_events=7, delay_seconds=2)
