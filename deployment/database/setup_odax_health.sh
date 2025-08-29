#!/usr/bin/env bash
set -euo pipefail

# ── Paths ───────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ENV_FILE_OVERRIDE:-$ROOT_DIR/.env}"

# Ensure .env exists
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env not found at: $ENV_FILE"
  exit 1
fi

# ── Helpers ────────────────────────────────────────────────────────────────────
clean_val() {  # strip CR (Windows) + trim
  printf '%s' "$1" | tr -d '\r' | sed -E 's/^[[:space:]]+|[[:space:]]+$//g'
}

# Read a single var strictly from .env in a CLEAN environment (ignores current env)
get_env_strict() {
  local name="$1"
  /usr/bin/env -i bash -c 'set -a; source "$1" 2>/dev/null; eval "printf %s \"\${'"$name"':-}\""' _ "$ENV_FILE"
}

# ── REQUIRED: POSTGRES_PASSWORD must be in .env ────────────────────────────────
POSTGRES_PASSWORD="$(clean_val "$(get_env_strict POSTGRES_PASSWORD)")"
if [ -z "$POSTGRES_PASSWORD" ]; then
  echo "❌ POSTGRES_PASSWORD must be set (non-empty) in $ENV_FILE"
  exit 1
fi

# ── Optional vars: read from .env (only), with sensible defaults ──────────────
POSTGRES_VERSION="$(clean_val "$(get_env_strict POSTGRES_VERSION)")"
POSTGRES_VERSION="${POSTGRES_VERSION:-15}"

CONTAINER_NAME="$(clean_val "$(get_env_strict CONTAINER_NAME)")"
CONTAINER_NAME="${CONTAINER_NAME:-odax-pg}"

POSTGRES_DB="$(clean_val "$(get_env_strict POSTGRES_DB)")"
POSTGRES_DB="${POSTGRES_DB:-odax_test}"

# Prefer HOST_PORT_HEALTH, else HOST_PORT, else 5433
HOST_PORT="${HOST_PORT:-$(clean_val "$(get_env_strict HOST_PORT)")}"
HOST_PORT="${HOST_PORT:-5433}"
if ! [[ "$HOST_PORT" =~ ^[0-9]+$ ]]; then
  echo "⚠️ Ungültiger Portwert '$HOST_PORT'. Fallback auf 5433."
  HOST_PORT=5433
fi

VOLUME_NAME="$(clean_val "$(get_env_strict VOLUME_NAME)")"
VOLUME_NAME="${VOLUME_NAME:-pgdata_odax}"

echo "📦 PostgreSQL mit Podman vorbereiten..."

# Volume erstellen (falls nicht vorhanden)
if ! podman volume exists "$VOLUME_NAME"; then
  echo "🔧 Erstelle Volume: $VOLUME_NAME"
  podman volume create "$VOLUME_NAME"
else
  echo "✔️ Volume $VOLUME_NAME existiert bereits"
fi

# Container stoppen & löschen, falls schon vorhanden
if podman container exists "$CONTAINER_NAME"; then
  echo "🛑 Stoppe alten Container..."
  podman stop "$CONTAINER_NAME"
  podman rm "$CONTAINER_NAME"
fi

# Container starten
echo "🚀 Starte PostgreSQL-Container: $CONTAINER_NAME"
podman run --name "$CONTAINER_NAME" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -v "$VOLUME_NAME":/var/lib/postgresql/data \
  -p "$HOST_PORT":5432 \
  -d docker.io/library/postgres:"$POSTGRES_VERSION"

# Warte, bis PostgreSQL bereit ist
echo "⏳ Warte 5 Sekunden auf PostgreSQL-Start..."
sleep 5




# Führe das SQL-Schema über podman exec + psql aus

echo "📋 Erstelle Datenbankschema..."
podman exec -i "$CONTAINER_NAME" psql -U postgres -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 <<'EOF'
CREATE TABLE IF NOT EXISTS sources (
  source_id        SERIAL PRIMARY KEY,
  name             TEXT NOT NULL,
  description      TEXT,
  url              TEXT,
  license          TEXT,
  raw_source_metadata JSONB
);

CREATE TABLE IF NOT EXISTS datasets (
  dataset_id       SERIAL PRIMARY KEY,
  source_id        INT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
  name             TEXT NOT NULL,
  description      TEXT,
  access_url       TEXT,
  update_timestamp TIMESTAMP,
  metadata         JSONB
);

CREATE TABLE IF NOT EXISTS cantons (
  canton_code  CHAR(2) PRIMARY KEY,
  name         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fee_regions (
  fee_region_id SERIAL PRIMARY KEY,
  canton_code   CHAR(2) NOT NULL REFERENCES cantons(canton_code) ON DELETE RESTRICT,
  region_no     SMALLINT NOT NULL,
  UNIQUE (canton_code, region_no)
);

CREATE TABLE IF NOT EXISTS municipalities (
  municipality_id SERIAL PRIMARY KEY,
  name            TEXT NOT NULL,
  canton_code     CHAR(2) NOT NULL REFERENCES cantons(canton_code) ON DELETE RESTRICT,
  fee_region_id   INT REFERENCES fee_regions(fee_region_id) ON DELETE SET NULL,
  UNIQUE (name, canton_code)
);

CREATE TABLE IF NOT EXISTS insurers (
  bag_number  INT PRIMARY KEY,
  name        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tariff_types (
  code  TEXT PRIMARY KEY,
  label TEXT
);

CREATE TABLE IF NOT EXISTS age_classes (
  code  TEXT PRIMARY KEY,
  label TEXT
);

CREATE TABLE IF NOT EXISTS age_subgroups (
  code            TEXT PRIMARY KEY,
  label           TEXT,
  age_class_code  TEXT NOT NULL REFERENCES age_classes(code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS franchises (
  amount INTEGER PRIMARY KEY CHECK (amount >= 0)
);

CREATE TABLE IF NOT EXISTS fees (
  fee_id             BIGSERIAL PRIMARY KEY,
  insurer_bag        INT NOT NULL REFERENCES insurers(bag_number) ON DELETE RESTRICT,
  canton_code        CHAR(2) NOT NULL REFERENCES cantons(canton_code) ON DELETE RESTRICT,
  fee_region_id      INT NOT NULL REFERENCES fee_regions(fee_region_id) ON DELETE RESTRICT,
  age_class_code     TEXT NOT NULL REFERENCES age_classes(code) ON DELETE RESTRICT,
  age_subgroup_code  TEXT REFERENCES age_subgroups(code) ON DELETE SET NULL,
  accident_included  BOOLEAN NOT NULL,
  franchise_amount   INTEGER NOT NULL REFERENCES franchises(amount) ON DELETE RESTRICT,
  tariff_type_code   TEXT NOT NULL REFERENCES tariff_types(code) ON DELETE RESTRICT,
  tariff_name        TEXT NOT NULL,
  valid_from         DATE NOT NULL DEFAULT DATE '1900-01-01',
  valid_to           DATE,
  currency           CHAR(3) NOT NULL DEFAULT 'CHF',
  monthly_premium    NUMERIC(12,2) NOT NULL,
  dataset_id         INT REFERENCES datasets(dataset_id) ON DELETE SET NULL,
  raw_source_metadata JSONB
);


BEGIN;
DO $$
BEGIN


  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.fees'::regclass
      AND conname = 'ux_fees_dedup'
  ) THEN
    ALTER TABLE public.fees
    ADD CONSTRAINT ux_fees_dedup UNIQUE (
      insurer_bag, canton_code, fee_region_id,
      age_class_code, age_subgroup_code, accident_included,
      franchise_amount, tariff_type_code, valid_from, tariff_name
    );
  END IF;
END $$;
COMMIT;




-- Indexes
CREATE INDEX IF NOT EXISTS idx_fees_lookup
  ON fees (canton_code, fee_region_id, age_class_code, accident_included, franchise_amount, tariff_type_code, tariff_name);

CREATE INDEX IF NOT EXISTS idx_fees_insurer
  ON fees (insurer_bag);

EOF


echo "✅ PostgreSQL-Container '$CONTAINER_NAME' mit Schema ist einsatzbereit!"