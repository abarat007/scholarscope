#!/bin/bash
# Runs once on a fresh pgdata volume: creates the dedicated Airflow database
# so the app database and Airflow metadata share one Postgres instance.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER airflow WITH PASSWORD 'airflow';
    CREATE DATABASE airflow OWNER airflow;
    CREATE USER langfuse WITH PASSWORD 'langfuse';
    CREATE DATABASE langfuse OWNER langfuse;
EOSQL
