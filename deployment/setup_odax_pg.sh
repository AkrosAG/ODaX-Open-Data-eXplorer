#!/bin/bash

# Konfiguration
CONTAINER_NAME="odax-pg"
POSTGRES_VERSION="15"
POSTGRES_PASSWORD="odax123"
POSTGRES_DB="odax_test"
HOST_PORT="5433"
VOLUME_NAME="pgdata_odax"

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

# SQL-Schema vorbereiten
SCHEMA_SQL=$(cat <<EOF
CREATE TABLE IF NOT EXISTS sources (
  source_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  url TEXT,
  license TEXT,
  raw_source_metadata JSONB
);

CREATE TABLE IF NOT EXISTS datasets (
  dataset_id SERIAL PRIMARY KEY,
  source_id INT NOT NULL REFERENCES sources(source_id),
  name TEXT NOT NULL,
  description TEXT,
  update_timestamp TIMESTAMP,
  access_url TEXT,
  metadata JSONB
);

CREATE TABLE IF NOT EXISTS data_entries (
  entry_id BIGSERIAL PRIMARY KEY,
  dataset_id INT NOT NULL REFERENCES datasets(dataset_id),
  identifier TEXT,
  created_at TIMESTAMP,
  content JSONB
);
EOF
)

# Führe das SQL-Schema über podman exec + psql aus
echo "📋 Erstelle Datenbankschema..."
podman exec -i "$CONTAINER_NAME" psql -U postgres -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 <<SQL
$SCHEMA_SQL
SQL

echo "✅ PostgreSQL-Container '$CONTAINER_NAME' mit Schema ist einsatzbereit!"
