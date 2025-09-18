
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

# ── Superset config ────────────────────────────────────────────────────────────
SUPERSET_CONTAINER_NAME="$(clean_val "$(get_env_strict SUPERSET_CONTAINER_NAME)")"
SUPERSET_CONTAINER_NAME="${SUPERSET_CONTAINER_NAME:-odax-superset}"

SUPERSET_PORT="$(clean_val "$(get_env_strict SUPERSET_PORT)")"
SUPERSET_PORT="${SUPERSET_PORT:-8088}"

POSTGRES_USER="$(clean_val "$(get_env_strict POSTGRES_USER)")"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

NETWORK_NAME="$(clean_val "$(get_env_strict NETWORK_NAME)")"
NETWORK_NAME="${NETWORK_NAME:-odax-net}"

SUPERSET_SECRET_KEY="$(clean_val "$(get_env_strict SUPERSET_SECRET_KEY)")"
if [ -z "$SUPERSET_SECRET_KEY" ]; then
  echo "🔑 Generiere zufälligen SUPERSET_SECRET_KEY (für Tests)…"
  SUPERSET_SECRET_KEY="$(python3 - <<'PY'
import secrets, string
alphabet = string.ascii_letters + string.digits
print(''.join(secrets.choice(alphabet) for _ in range(64)))
PY
)"
fi

SUPERSET_ADMIN_USERNAME="$(clean_val "$(get_env_strict SUPERSET_ADMIN_USERNAME)")"
SUPERSET_ADMIN_USERNAME="${SUPERSET_ADMIN_USERNAME:-admin}"

SUPERSET_ADMIN_PASSWORD="$(clean_val "$(get_env_strict SUPERSET_ADMIN_PASSWORD)")"
if [ -z "$SUPERSET_ADMIN_PASSWORD" ]; then
  echo "❌ SUPERSET_ADMIN_PASSWORD must be set (non-empty) in $ENV_FILE"
  exit 1
fi
SUPERSET_ADMIN_EMAIL="$(clean_val "$(get_env_strict SUPERSET_ADMIN_EMAIL)")"
SUPERSET_ADMIN_EMAIL="${SUPERSET_ADMIN_EMAIL:-admin@example.com}"

# ── Network (so Superset can reach Postgres by container name) ────────────────
if ! podman network exists "$NETWORK_NAME"; then
  echo "🔧 Creating network: $NETWORK_NAME"
  podman network create "$NETWORK_NAME"
else
  echo "✔️ Network $NETWORK_NAME already exists"
fi

# Re-run Postgres with network if needed
echo "🔗 Ensuring Postgres '$CONTAINER_NAME' is on $NETWORK_NAME"
if podman container exists "$CONTAINER_NAME"; then
  podman inspect "$CONTAINER_NAME" | grep -q "\"$NETWORK_NAME\"" || {
    echo "↻ Restarting Postgres on $NETWORK_NAME"
    podman stop "$CONTAINER_NAME" || true
    podman rm "$CONTAINER_NAME" || true
    podman run --name "$CONTAINER_NAME" \
      --network "$NETWORK_NAME" \
      -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
      -e POSTGRES_DB="$POSTGRES_DB" \
      -e POSTGRES_USER="$POSTGRES_USER" \
      -v "$VOLUME_NAME":/var/lib/postgresql/data \
      -p "$HOST_PORT":5432 \
      -d docker.io/library/postgres:"$POSTGRES_VERSION"
    echo "⏳ Waiting 5s for Postgres…"; sleep 5
  }
else
  echo "❌ Expected Postgres container '$CONTAINER_NAME' to exist"
  exit 1
fi

# ── Start Superset ────────────────────────────────────────────────────────────
# DB URI for Superset metadata -> use the Postgres container name as host:
SUPERMETA_URI="postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${CONTAINER_NAME}:5432/${POSTGRES_DB}"

# Remove old Superset container if present
if podman container exists "$SUPERSET_CONTAINER_NAME"; then
  echo "🛑 Stop & remove old Superset…"
  podman stop "$SUPERSET_CONTAINER_NAME" || true
  podman rm "$SUPERSET_CONTAINER_NAME" || true
fi

echo "🚀 Starting Superset container: $SUPERSET_CONTAINER_NAME"
podman run --name "$SUPERSET_CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  -e SUPERSET_SECRET_KEY="$SUPERSET_SECRET_KEY" \
  -e SQLALCHEMY_DATABASE_URI="$SUPERMETA_URI" \
  -p "$SUPERSET_PORT":8088 \
  -d docker.io/apache/superset:latest-py311

echo "⏳ Waiting 10s for Superset container to boot…"
sleep 10
podman exec $SUPERSET_CONTAINER_NAME pip install --upgrade pip
podman exec $SUPERSET_CONTAINER_NAME pip install --no-cache-dir pillow


# ── Initialize Superset & create admin ────────────────────────────────────────
echo "🗃️  Applying DB migrations…"
podman exec "$SUPERSET_CONTAINER_NAME" superset db upgrade

echo "👤 Creating admin user…"
podman exec "$SUPERSET_CONTAINER_NAME" superset fab create-admin \
  --username "$SUPERSET_ADMIN_USERNAME" \
  --firstname Admin --lastname User \
  --email "$SUPERSET_ADMIN_EMAIL" \
  --password "$SUPERSET_ADMIN_PASSWORD"

echo "🔧 Finalizing init…"
podman exec "$SUPERSET_CONTAINER_NAME" superset init

echo "✅ Superset up at http://localhost:${SUPERSET_PORT}"


# Warte, bis PostgreSQL bereit ist
echo "⏳ Warte 5 Sekunden auf PostgreSQL-Start..."
sleep 5
echo "📋 Erstelle Datenbankschema..."
podman exec -i "$CONTAINER_NAME" psql -U postgres -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 -v schema="airq" <<'EOSQL'
DO $do$
BEGIN
  -- psql ersetzt :'schema' zu einem SQL-String-Literal (z.B. 'airq')
  EXECUTE format('CREATE SCHEMA IF NOT EXISTS airq');
END
$do$;


SELECT set_config('search_path', :'schema' || ', public', false);


-- Allgemeine Metadaten-Tabellen (wiederverwendbar)
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

-- Lookup / Klassifikationen
CREATE TABLE IF NOT EXISTS pollutants (
  code        TEXT PRIMARY KEY,      -- z.B. 'CO','NO2','PM10','PM2_5','O3'
  label       TEXT,                  -- lesbarer Name
  unit        TEXT,                  -- Standard-Einheit, z.B. 'µg/m3' oder 'mg/m3'
  metadata    JSONB
);

-- Stationen (inkl. Koordinaten in LV95 und WGS84, falls verfügbar)
CREATE TABLE IF NOT EXISTS stations (
  station_id       SERIAL PRIMARY KEY,
  external_id      TEXT UNIQUE,              -- z.B. 'BASEL-BINNINGEN' oder OGC FID/ID
  short_code       TEXT,                     -- z.B. 'BAS'
  name             TEXT NOT NULL,
  canton_code      CHAR(2),                  -- optional: 'ZH', 'BE', ...
  lv95_easting     NUMERIC(12,3),            -- EPSG:2056
  lv95_northing    NUMERIC(12,3),            -- EPSG:2056
  wgs84_lon        DOUBLE PRECISION,         -- EPSG:4326
  wgs84_lat        DOUBLE PRECISION,         -- EPSG:4326
  elevation_m      NUMERIC(8,2),
  location_type    TEXT,                     -- z.B. 'Städtisch', 'Ländlich', ...
  remarks          TEXT,
  dataset_id       INT REFERENCES datasets(dataset_id) ON DELETE SET NULL,
  metadata         JSONB
);


-- Zeitreihen-Messungen je Station/Schadstoff/Zeitpunkt
-- Werte können unterschiedlichste Einheiten haben; die Normalisierung kann separat passieren.
CREATE TABLE IF NOT EXISTS station_measurements (
  measurement_id    BIGSERIAL PRIMARY KEY,
  station_id        INT NOT NULL REFERENCES stations(station_id) ON DELETE CASCADE,
  pollutant_code    TEXT NOT NULL REFERENCES pollutants(code) ON DELETE RESTRICT,
  ts_utc            TIMESTAMPTZ NOT NULL, -- Messzeitpunkt in UTC
  value             DOUBLE PRECISION,     -- Messwert
  unit              TEXT,                 -- Einheit des konkreten Datensatzes
  quality_flag      TEXT,                 -- optional: Qualität/Validität
  dataset_id        INT REFERENCES datasets(dataset_id) ON DELETE SET NULL,
  raw_source_metadata JSONB,
  -- Eindeutige Messung je Station/Schadstoff/Zeitpunkt (idempotent importierbar)
  UNIQUE (station_id, pollutant_code, ts_utc)
);

-- Abgeleitete tägliche Aggregation (Median/Mean etc.) – optional, aber häufig praktisch
CREATE TABLE IF NOT EXISTS station_daily (
  station_daily_id  BIGSERIAL PRIMARY KEY,
  station_id        INT NOT NULL REFERENCES stations(station_id) ON DELETE CASCADE,
  pollutant_code    TEXT NOT NULL REFERENCES pollutants(code) ON DELETE RESTRICT,
  date_utc          DATE NOT NULL,
  agg_value         DOUBLE PRECISION,     -- z.B. Median oder Mittelwert des Tages
  unit              TEXT,
  method            TEXT DEFAULT 'median', -- 'median' | 'mean' etc.
  dataset_id        INT REFERENCES datasets(dataset_id) ON DELETE SET NULL,
  metadata          JSONB,
  UNIQUE (station_id, pollutant_code, date_utc, method)
);

-- Sinnvolle Indizes für typische Abfragen
CREATE INDEX IF NOT EXISTS ix_station_measurements_station_ts
  ON station_measurements (station_id, ts_utc);
CREATE INDEX IF NOT EXISTS ix_station_measurements_pollutant_ts
  ON station_measurements (pollutant_code, ts_utc);
CREATE INDEX IF NOT EXISTS ix_station_measurements_ts
  ON station_measurements (ts_utc);

CREATE INDEX IF NOT EXISTS ix_station_daily_station_date
  ON station_daily (station_id, date_utc);
CREATE INDEX IF NOT EXISTS ix_station_daily_pollutant_date
  ON station_daily (pollutant_code, date_utc);

EOSQL

echo "✅ PostgreSQL-Container '$CONTAINER_NAME' mit Luftqualitäts-Schema ist einsatzbereit!"