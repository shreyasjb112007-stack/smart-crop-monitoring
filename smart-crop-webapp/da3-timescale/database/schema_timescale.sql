-- ============================================================
-- schema_timescale.sql
-- DA3: Time-series sensor data (soil moisture, temperature,
-- humidity) from the Raspberry Pi + sensors, linked back to the
-- SAME Farm entity used in DA1/DA2 (Farm_ID is a plain foreign
-- key reference -- Farm itself still lives in MySQL, this DB
-- only stores the high-frequency sensor stream).
--
-- Run on your lab machine (or wherever this DB lives) with:
--   psql -U cropapp -d smartfarmsensors -f schema_timescale.sql
-- ============================================================

-- Real TimescaleDB install (do this once, on Ubuntu/Raspberry Pi OS):
--   sudo apt install gnupg postgresql-common apt-transport-https lsb-release
--   sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
--   echo "deb https://packagecloud.io/timescale/timescaledb/$(lsb_release -is | tr 'A-Z' 'a-z')/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
--   wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
--   sudo apt update && sudo apt install timescaledb-2-postgresql-16
--   sudo timescaledb-tune --quiet --yes
--   sudo systemctl restart postgresql
-- Then uncomment the CREATE EXTENSION line below.

-- CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS SensorReading (
    Reading_ID   BIGSERIAL,
    Farm_ID      INT NOT NULL,          -- references Farm(Farm_ID) in MySQL (cross-DB, no FK enforced here)
    Sensor_Type  VARCHAR(20) NOT NULL,  -- 'soil_moisture' | 'temperature' | 'humidity'
    Value        DECIMAL(6,2) NOT NULL,
    Unit         VARCHAR(10) NOT NULL,  -- '%', 'C', '%RH'
    Recorded_At  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (Reading_ID, Recorded_At)
);

-- Turn this into a TimescaleDB hypertable (real deployment only --
-- this is what actually gives you the time-series performance benefit:
-- automatic time-based partitioning under the hood).
-- SELECT create_hypertable('sensorreading', 'recorded_at', if_not_exists => TRUE);

-- Index used heavily by the dashboard queries below (works with or
-- without the hypertable conversion).
CREATE INDEX IF NOT EXISTS idx_sensor_farm_time
    ON SensorReading (Farm_ID, Sensor_Type, Recorded_At DESC);

-- Optional: alert thresholds per farm, so "moisture too low" can be
-- flagged without hardcoding numbers in application code.
CREATE TABLE IF NOT EXISTS SensorThreshold (
    Farm_ID      INT NOT NULL,
    Sensor_Type  VARCHAR(20) NOT NULL,
    Min_Value    DECIMAL(6,2),
    Max_Value    DECIMAL(6,2),
    PRIMARY KEY (Farm_ID, Sensor_Type)
);
