#!/bin/bash
set -euo pipefail

PGHOST=${PGHOST:-127.0.0.1}
PGPORT=${PGPORT:-5432}
PGDATABASE=${PGDATABASE:-odax}
PGUSER=${PGUSER:-odax}

if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "❌ PGPASSWORD is not set. Export PGPASSWORD or configure a ~/.pgpass file."
  exit 1
fi

psql "host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" -v ON_ERROR_STOP=1 <<SQL
SELECT 'table_rows' AS metric, COUNT(*) AS value FROM odax.healthinsurance_premiums;
SELECT 'distinct_cantons' AS metric, COUNT(DISTINCT canton) AS value FROM odax.healthinsurance_premiums;
SELECT 'sample' AS metric, * FROM odax.healthinsurance_premiums LIMIT 5;
SQL
