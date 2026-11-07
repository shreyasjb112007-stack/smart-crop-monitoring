#!/bin/bash
# ============================================================
# setup_database.sh
# One-shot MySQL setup: creates the app DB user, the SmartCropDB
# database, loads the schema, seed data, and stored procedures.
#
# Usage:
#   chmod +x setup_database.sh
#   ./setup_database.sh
#
# Prerequisite: MySQL server installed and running, and you know
# your MySQL root password (you'll be prompted for it).
# ============================================================

set -e

echo "This will create a MySQL user 'cropapp' and a database 'SmartCropDB'."
read -p "Enter your MySQL root password: " -s ROOT_PASS
echo ""

mysql -u root -p"$ROOT_PASS" <<SQL
CREATE USER IF NOT EXISTS 'cropapp'@'localhost' IDENTIFIED BY 'cropapp_pass';
CREATE DATABASE IF NOT EXISTS SmartCropDB;
GRANT ALL PRIVILEGES ON SmartCropDB.* TO 'cropapp'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "Loading schema..."
mysql -u cropapp -pcropapp_pass SmartCropDB < database/schema.sql

echo "Loading seed data..."
mysql -u cropapp -pcropapp_pass SmartCropDB < database/seed_data.sql

echo "Loading stored procedures..."
mysql -u cropapp -pcropapp_pass SmartCropDB < database/procedures.sql

echo ""
echo "Done. SmartCropDB is ready."
echo "  Host: localhost   User: cropapp   Password: cropapp_pass   DB: SmartCropDB"
echo "(Change these in app/db.py if you want different credentials.)"
