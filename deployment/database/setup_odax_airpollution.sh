
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
HOST_PORT="$(clean_val "$(get_env_strict HOST_PORT)")"
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

echo "📋 Erstelle Datenbankschema für Luftqualitätsdaten..."
podman exec -i "$CONTAINER_NAME" psql -U postgres -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 <<'EOF'
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
  metadata         JSONB
);

-- Optionale Verknüpfung Station <-> Dataset (z.B. Herkunft aus STAC)
CREATE TABLE IF NOT EXISTS station_assets (
  station_asset_id  SERIAL PRIMARY KEY,
  station_id        INT NOT NULL REFERENCES stations(station_id) ON DELETE CASCADE,
  dataset_id        INT REFERENCES datasets(dataset_id) ON DELETE SET NULL,
  asset_name        TEXT NOT NULL,       -- z.B. Dateiname, Asset-Key aus STAC
  access_url        TEXT,                -- Download-URL
  checksum          TEXT,
  file_size_bytes   BIGINT,
  mime_type         TEXT,
  time_range        TSRANGE,             -- optionaler Zeitraum, den das Asset abdeckt
  metadata          JSONB,
  UNIQUE (station_id, asset_name)
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

-- Beispiel-View: Letzter Messwert je Station/Schadstoff
CREATE OR REPLACE VIEW vw_latest_station_values AS
SELECT DISTINCT ON (m.station_id, m.pollutant_code)
  m.station_id,
  m.pollutant_code,
  m.ts_utc,
  m.value,
  m.unit,
  m.dataset_id
FROM station_measurements m
ORDER BY m.station_id, m.pollutant_code, m.ts_utc DESC;

-- Beispiel-View: Stations-Metadaten kompakt
CREATE OR REPLACE VIEW vw_stations_compact AS
SELECT
  s.station_id, s.external_id, s.short_code, s.name,
  s.canton_code, s.wgs84_lat, s.wgs84_lon, s.elevation_m, s.location_type
FROM stations s;

-- Ein paar gängige Schadstoff-Codes vorbesetzen (idempotent)
INSERT INTO pollutants (code, label, unit)
VALUES
 ('CO',  'Kohlenmonoxid', 'mg/m3'),
 ('NO2', 'Stickstoffdioxid', 'µg/m3'),
 ('PM10','Feinstaub PM10',  'µg/m3'),
 ('PM2_5','Feinstaub PM2.5','µg/m3'),
 ('O3',  'Ozon',            'µg/m3')
ON CONFLICT (code) DO UPDATE SET
  label = EXCLUDED.label,
  unit  = EXCLUDED.unit;

EOF

echo "✅ PostgreSQL-Container '$CONTAINER_NAME' mit Luftqualitäts-Schema ist einsatzbereit!"