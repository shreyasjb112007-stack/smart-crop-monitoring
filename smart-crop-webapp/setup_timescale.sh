#!/bin/bash
# ============================================================
# setup_timescale.sh
# One-shot PostgreSQL/TimescaleDB setup for DA3 sensor data.
#
# Usage:
#   chmod +x setup_timescale.sh
#   ./setup_timescale.sh
#
# Prerequisite: PostgreSQL installed and running.
#   Ubuntu/Debian/Raspberry Pi OS: sudo apt install postgresql
#   (TimescaleDB extension itself is optional -- see the comment
#    block at the top of database/schema_timescale.sql for how to
#    add it. Plain PostgreSQL works fine for the demo/queries.)
# ============================================================

set -e

echo "This will create a PostgreSQL user 'cropapp' and a database 'smartfarmsensors'."

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'cropapp') THEN
      CREATE USER cropapp WITH PASSWORD 'cropapp_pass';
   END IF;
END
\$\$;
SQL

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'smartfarmsensors'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE smartfarmsensors OWNER cropapp;"

echo "Loading schema..."
PGPASSWORD=cropapp_pass psql -h localhost -U cropapp -d smartfarmsensors -f da3-timescale/database/schema_timescale.sql

echo ""
echo "Done. smartfarmsensors is ready."
echo "  Host: localhost   User: cropapp   Password: cropapp_pass   DB: smartfarmsensors"
echo "(Change these in da3-timescale/db_timescale.py if you want different credentials.)"
