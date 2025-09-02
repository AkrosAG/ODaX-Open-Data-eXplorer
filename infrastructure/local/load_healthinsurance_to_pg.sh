#!/bin/bash
set -euo pipefail

# This script loads the health insurance premiums CSV into PostgreSQL
# Requirements:
# - A running Postgres (e.g., started via setup_odax_pg.sh) reachable via host/port
# - psql installed in the environment
# - CSV source file present in data/healthinsurance/Prämien_CH.csv
#
# Usage:
#   ./infrastructure/local/load_healthinsurance_to_pg.sh
#
# Config via env vars (with defaults):
#   PGHOST (default: 127.0.0.1)
#   PGPORT (default: 5432)
#   PGDATABASE (default: odax)
#   PGUSER (default: odax)
#   PGPASSWORD (must be set or provided via ~/.pgpass or env/secret)

PGHOST=${PGHOST:-127.0.0.1}
PGPORT=${PGPORT:-5432}
PGDATABASE=${PGDATABASE:-odax}
PGUSER=${PGUSER:-odax}

# Ensure PGPASSWORD is provided somehow
if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "❌ PGPASSWORD is not set. Export PGPASSWORD or configure a ~/.pgpass file."
  echo "   Example (Podman Secret):"
  echo "   export PGPASSWORD=deinPasswort"
  exit 1
fi

# Paths
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
INIT_SQL="$SCRIPT_DIR/init_odax_healthinsurance.sql"
CSV_PATH="$REPO_ROOT/data/healthinsurance/Prämien_CH.csv"

if [[ ! -f "$CSV_PATH" ]]; then
  echo "❌ CSV not found: $CSV_PATH"
  exit 1
fi

# Create schema and table
psql "host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" \
  -v ON_ERROR_STOP=1 \
  -f "$INIT_SQL"

# Truncate before loading to keep it idempotent
psql "host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" -v ON_ERROR_STOP=1 -c "TRUNCATE odax.healthinsurance_premiums;"

# Set correct client encoding for Latin-1 CSV
psql "host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" -v ON_ERROR_STOP=1 -c "SET client_encoding TO 'LATIN1';"

# Perform client-side \copy from CSV with semicolon delimiter and header
# Note: Using \copy allows referencing a local file path without server-side access.
psql "host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" -v ON_ERROR_STOP=1 <<SQL
SET client_encoding TO 'LATIN1';
\\copy odax.healthinsurance_premiums (
  insurer_bag_code,
  canton,
  territory,
  business_year,
  survey_year,
  fee_region,
  age_class,
  accident_coverage,
  tariff_code,
  tariff_type,
  sub_age_group,
  franchise_level_code,
  franchise_label,
  premium_chf,
  is_base_p,
  is_base_f,
  tariff_label
)
FROM '$CSV_PATH' WITH (
  FORMAT csv,
  HEADER true,
  DELIMITER ';',
  NULL '',
  QUOTE '"'
);
SQL

echo "✅ Loaded health insurance premiums into odax.healthinsurance_premiums"
