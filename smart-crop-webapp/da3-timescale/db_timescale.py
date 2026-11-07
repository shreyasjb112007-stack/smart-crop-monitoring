"""
db_timescale.py
----------------
Connection helper for the DA3 sensor database (TimescaleDB/PostgreSQL).
Separate from app/db.py (MySQL) on purpose -- this is a genuinely
different database technology, not just a second table set.
"""

import psycopg2
import psycopg2.extras

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "cropapp",
    "password": "cropapp_pass",
    "dbname": "smartfarmsensors",   # lowercase -- Postgres folds unquoted identifiers
}


def get_connection():
    return psycopg2.connect(**PG_CONFIG)


def insert_reading(farm_id: int, sensor_type: str, value: float, unit: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO SensorReading (Farm_ID, Sensor_Type, Value, Unit) VALUES (%s,%s,%s,%s)",
                (farm_id, sensor_type, value, unit),
            )
        conn.commit()
    finally:
        conn.close()


def latest_readings(farm_id: int):
    """One row per sensor type: its most recent value."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT DISTINCT ON (Sensor_Type) Sensor_Type, Value, Unit, Recorded_At
                   FROM SensorReading WHERE Farm_ID=%s
                   ORDER BY Sensor_Type, Recorded_At DESC""",
                (farm_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def hourly_averages(farm_id: int, sensor_type: str, hours: int = 24):
    """Time-bucketed averages for charting (last N hours)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT date_trunc('hour', Recorded_At) AS bucket, ROUND(AVG(Value),2) AS avg_value
                   FROM SensorReading
                   WHERE Farm_ID=%s AND Sensor_Type=%s
                     AND Recorded_At > NOW() - (%s || ' hours')::interval
                   GROUP BY bucket ORDER BY bucket""",
                (farm_id, sensor_type, hours),
            )
            return cur.fetchall()
    finally:
        conn.close()


def check_alerts(farm_id: int):
    """Returns any sensor currently outside its configured threshold."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """WITH latest AS (
                       SELECT DISTINCT ON (Sensor_Type) Sensor_Type, Value, Recorded_At
                       FROM SensorReading WHERE Farm_ID=%s
                       ORDER BY Sensor_Type, Recorded_At DESC
                   )
                   SELECT l.Sensor_Type, l.Value, st.Min_Value, st.Max_Value, l.Recorded_At
                   FROM latest l
                   JOIN SensorThreshold st ON st.Farm_ID=%s AND st.Sensor_Type=l.Sensor_Type
                   WHERE l.Value < st.Min_Value OR l.Value > st.Max_Value""",
                (farm_id, farm_id),
            )
            return cur.fetchall()
    finally:
        conn.close()
