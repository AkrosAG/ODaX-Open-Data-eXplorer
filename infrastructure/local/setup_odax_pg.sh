#!/bin/bash

# Container-Konfiguration
CONTAINER_NAME="odax-postgres"
DB_NAME="odax"
DB_USER="odax"
SECRET_NAME="pg_password"
PORT="5432"

# Prüfen, ob Secret existiert
if ! podman secret inspect "$SECRET_NAME" &>/dev/null; then
  echo "❌ Secret '$SECRET_NAME' wurde nicht gefunden. Bitte mit folgendem Befehl erstellen:"
  echo '   echo "deinPasswort" | podman secret create pg_password -'
  exit 1
fi

# Container starten
podman run -d \
  --name $CONTAINER_NAME \
  -p $PORT:5432 \
  --secret $SECRET_NAME,type=env,target=POSTGRES_PASSWORD \
  -e POSTGRES_DB=$DB_NAME \
  -e POSTGRES_USER=$DB_USER \
  docker.io/library/postgres:15

echo "✅ PostgreSQL läuft jetzt mit Secret '$SECRET_NAME' auf Port $PORT."
echo "ℹ️  DB: $DB_NAME | User: $DB_USER"
echo "👉 Exportieren Sie das gleiche Passwort für psql: export PGPASSWORD=... (sollte dem in 'pg_password' entsprechen)"
