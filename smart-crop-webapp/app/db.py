"""
db.py
-----
Thin MySQL connection helper used by the Flask app (app/main.py).
Uses PyMySQL, talks to the SmartCropDB database created by
database/schema.sql + database/procedures.sql.
"""

import pymysql
import pymysql.cursors

DB_CONFIG = {
    "host": "localhost",
    "user": "cropapp",
    "password": "cropapp_pass",
    "database": "SmartCropDB",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def run_query(sql: str, params: tuple = (), fetch: str = "all"):
    """
    fetch: "all" -> fetchall, "one" -> fetchone, "none" -> no fetch (INSERT/UPDATE)
    Returns the last inserted row id when fetch="none" and it's an INSERT.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch == "all":
                return cur.fetchall()
            elif fetch == "one":
                return cur.fetchone()
            else:
                return cur.lastrowid
    finally:
        conn.close()


def call_procedure(proc_name: str, params: tuple = ()):
    """
    Calls a stored procedure and returns ALL result sets it produces
    (some procedures, like GetDiseaseReport, return more than one).
    Returns a list of result-sets, each a list of dict rows.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.callproc(proc_name, params)
            result_sets = [cur.fetchall()]
            while cur.nextset():
                result_sets.append(cur.fetchall())
            return result_sets
    finally:
        conn.close()
