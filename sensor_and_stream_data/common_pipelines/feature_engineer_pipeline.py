# pipelines/features_pipeline.py

from datetime import datetime
import apache_beam as beam


def debug_combined_count(kv: tuple) -> tuple:
    station_id, count = kv
    print(f"Combined count: station={station_id}, count={count}")
    return kv

def log_elements(kv: tuple):
    # NOTE: this def log_elements(msg: str, element: tuple):  and
    # | "LogElements" >> beam.Map(lambda element: log_elements("Counting Pickups",element)) <=  DO NOT WORK
    print("[DEBUG] Counting Pickups")
    print(f"[DEBUG] Processing element: {kv}")
    return kv

class LogElements(beam.DoFn):
    
    def __init__(self, msg):
        self.log_msg = msg

    # NOTE: this way is more clear. We receive elements, log our msg and return the input element
    def process(self, element):
        print(f"{self.log_msg}")
        print(f"[DEBUG] Processing element: {element}")
        yield element


def build_features_pipeline(
    p: beam.Pipeline,
    raw_events: beam.PCollection,
) -> beam.PCollection:
    """
    Builds the feature engineering pipeline.
    Input:
        raw_events: PCollection[Dict]
    Output:
        PCollection[List[Dict]]  (batched for MERGE)
    """


    # NOTE: 30-minute window for pickup_count
    # Called PCollections in data beam. It is a stream of elements (not a list of dictionaries.)
    # Each PCollection is a distributed dataset that can be processed in parallel.
    # You can think that the pipe process this elements one by one sequential or in parallel (distributed)
    pickup_30min = (
        raw_events
        # NOTE: tells beam to keep data in 30-minute fixed windows
        # inputs and outputs are the same (raw_events rows)
        # {
        #     'station_id': 'A_101',
        #     'ts_iso': datetime(...),
        #     'kind': 'pickup',
        #     ...
        # }
        | "Window30Min" >> beam.WindowInto(beam.window.FixedWindows(30 * 60))
        # NOTE: keep only pickup events
        | "FilterPickups" >> beam.Filter(lambda r: r['kind'] == 'pickup')
        # NOTE: Converts each event row into a (key=station_id, value=1) tuple
        # inputs {'station_id': 'A_101', 'ts_iso': ..., 'kind': 'pickup', ...}
        # outputs ('A_101', 1)
        | "KeyByStation" >> beam.Map(lambda r: (r['station_id'], 1))
        # NOTE: this step receive the (station_id, 1) tuples, do the logs and than return the input elements unchanged
        # That is why it works without breaking the pipeline
        #| "LogElements" >> beam.ParDo(LogElements("Counting Pickups")) 
        #| "LogElements" >> beam.Map(log_elements) 
        # NOTE: Sum up the counts per station_id key
        # inputs: [('A_101', 1), ('A_101', 1), ('A_205', 1)]
        # outputs: ('A_101', 2), ('A_205', 1)
        | "CountPickups" >> beam.CombinePerKey(sum)
        # NOTE: added debug step to log formatted pickup rows
        # | "DebugPickupCounts" >> beam.Map(debug_combined_count)
        # NOTE: Format into feature dict
        # inputs: ('A_101', 2), 'A_205', 1)
        # outputs: 
        # {
        #     'station_id': 'A_101',
        #     'feature_name': 'pickup_count',
        #     'window_len': '30m',
        #     'value': 2.0,
        #     'as_of': '2025-10-18T16:30:00Z'  # current UTC time
        # 
        | "FormatPickup30" >> beam.Map(lambda kv: {
            'station_id': kv[0],
            'feature_name': 'pickup_count',
            'window_len': '30m',
            'value': float(kv[1]),
            'as_of': datetime.utcnow().isoformat()
        })
    )

    # NOTE: 60-minute window for dropoff_count
    # Called PCollections in data beam. It is a stream of elements (not a list of dictionaries.)
    # Each PCollection is a distributed dataset that can be processed in parallel.
    # You can think that the pipe process this elements one by one sequential or in parallel (distributed)
    dropoff_60min = (
        raw_events
        | "Window60Min" >> beam.WindowInto(beam.window.FixedWindows(60 * 60))
        | "FilterDropoffs" >> beam.Filter(lambda r: r['kind'] == 'dropoff')
        | "KeyByStationDrop" >> beam.Map(lambda r: (r['station_id'], 1))
        | "CountDropoffs" >> beam.CombinePerKey(sum)
        | "FormatDropoff60" >> beam.Map(lambda kv: {
            'station_id': kv[0],
            'feature_name': 'dropoff_count',
            'window_len': '60m',
            'value': float(kv[1]),
            'as_of': datetime.utcnow().isoformat()
        })
    )

    # NOTE: Flatten both feature streams
    # merges the PCollections pickup_30min and dropoff_60min into a single PCollection
    # pickup_30min: {'station_id': 'A_101', 'feature_name': 'pickup_count', 'window_len': '30m', 'value': 5, 'as_of': ...}
    # dropoff_60min: {'station_id': 'A_101', 'feature_name': 'dropoff_count', 'window_len': '60m', 'value': 8, 'as_of': ...}
    # output PCollections:
    #  all_features:  
    #    {'station_id': 'A_101', 'feature_name': 'pickup_count', ...},
    #    {'station_id': 'A_101', 'feature_name': 'dropoff_count', ...}
    all_features = (
        (pickup_30min, dropoff_60min)
        | "FlattenAllFeatures" >> beam.Flatten()
    )

    # NOTE: Group into batches to feed into upsert
    # merge all elements of PCollections into a single list of dictionaries
    # This load all elements into memory (Similar to collect() / groupBy().agg() in Spark)
    # For large scale, consider using smaller batches beam.util.(GroupIntoBatches(500))
    grouped = (
        all_features
        | "BatchForMerge" >> beam.combiners.ToList().without_defaults()
    )

    return grouped
