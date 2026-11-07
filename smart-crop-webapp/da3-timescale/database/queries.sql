-- ============================================================
-- queries.sql
-- DA3 "core operations / technology-specific queries" demo set.
-- These are exactly the kind of queries that are painful/slow in
-- a plain relational table but natural in a time-series DB.
-- ============================================================

-- 1. INSERT a batch of readings (what the Pi script does every N seconds)
INSERT INTO SensorReading (Farm_ID, Sensor_Type, Value, Unit, Recorded_At)
VALUES
    (1, 'soil_moisture', 42.5, '%',   NOW()),
    (1, 'temperature',   29.1, 'C',   NOW()),
    (1, 'humidity',      68.0, '%RH', NOW());

-- 2. LATEST reading per sensor type for a farm (dashboard "current status")
SELECT DISTINCT ON (Sensor_Type)
    Sensor_Type, Value, Unit, Recorded_At
FROM SensorReading
WHERE Farm_ID = 1
ORDER BY Sensor_Type, Recorded_At DESC;

-- 3. TIME-RANGE query: last 24 hours of soil moisture for a farm
SELECT Recorded_At, Value
FROM SensorReading
WHERE Farm_ID = 1
  AND Sensor_Type = 'soil_moisture'
  AND Recorded_At > NOW() - INTERVAL '24 hours'
ORDER BY Recorded_At;

-- 4. TIME-BUCKETED aggregation: hourly average temperature (what a
-- graph/chart on the dashboard would plot). Uses date_trunc here
-- (works on plain Postgres); on a real TimescaleDB hypertable you'd
-- use the faster time_bucket('1 hour', recorded_at) instead --
-- same result, purpose-built for this exact query pattern.
SELECT
    date_trunc('hour', Recorded_At) AS bucket,
    ROUND(AVG(Value), 2) AS avg_temperature
FROM SensorReading
WHERE Farm_ID = 1 AND Sensor_Type = 'temperature'
GROUP BY bucket
ORDER BY bucket;

-- 5. THRESHOLD / ALERT query: any farm currently below its configured
-- minimum soil moisture (using each farm's latest reading)
WITH latest_moisture AS (
    SELECT DISTINCT ON (Farm_ID)
        Farm_ID, Value, Recorded_At
    FROM SensorReading
    WHERE Sensor_Type = 'soil_moisture'
    ORDER BY Farm_ID, Recorded_At DESC
)
SELECT lm.Farm_ID, lm.Value AS current_moisture, st.Min_Value AS threshold, lm.Recorded_At
FROM latest_moisture lm
JOIN SensorThreshold st
    ON st.Farm_ID = lm.Farm_ID AND st.Sensor_Type = 'soil_moisture'
WHERE lm.Value < st.Min_Value;

-- 6. RETENTION-style cleanup: delete readings older than 30 days
-- (on a real hypertable you'd instead use TimescaleDB's built-in
-- add_retention_policy() to automate this -- shown here as a plain
-- DELETE so it works identically with or without the extension).
DELETE FROM SensorReading WHERE Recorded_At < NOW() - INTERVAL '30 days';
