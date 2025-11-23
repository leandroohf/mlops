-- NOTE: procedure to upsert station features into the feature event table
--   flaten table. convert feature_table_wide to long format
--   Make easy to add new features if the table is not wide
--   | station_id | feature_name     | window_len | value | as_of                |
--   |------------+------------------+------------+-------+----------------------|
--   | A_101      | pickups_count    | 15m        |     7 | 2025-10-18T16:25:01Z |
--   | A_101      | inflow_velocity  | 15m        |   0.4 | 2025-10-18T16:25:01Z |
MERGE `${FEATURE_EVENT_TABLE}` T
USING (
    -- NOTE: pickup feature
      SELECT
        station_id,
        'pickup_count' AS feature_name,
        '5h' AS window_len,
        COUNTIF(kind = 'pickup') AS value,
        CURRENT_TIMESTAMP() AS as_of

      FROM
        `${RAW_EVENT_TABLE}`
      WHERE
        ts_iso >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 HOUR)
      GROUP BY
        station_id

      UNION ALL

      -- NOTE: dropoff feature
      SELECT
        station_id,
        'dropoff_count' AS feature_name,
        '5h' AS window_len,
        COUNTIF(kind = 'dropoff') AS value,
        CURRENT_TIMESTAMP() AS as_of

      FROM
        `${RAW_EVENT_TABLE}`
      WHERE
        ts_iso >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 HOUR)
      GROUP BY
        station_id
) S
ON
  T.station_id = S.station_id AND
  T.feature_name = S.feature_name AND
  T.window_len = S.window_len AND
  T.as_of = S.as_of  -- Optional: set to overwrite same timestamp

-- update
WHEN MATCHED THEN
  UPDATE SET value = S.value

-- just insert
WHEN NOT MATCHED THEN
  INSERT (station_id, feature_name, window_len, value, as_of)
  VALUES (S.station_id, S.feature_name, S.window_len, S.value, S.as_of);