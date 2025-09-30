
------------------------------ CREATE SCHEME FOR HEALTHINSURANCE ------------------------------
Create schema if not exists health;

SELECT set_config('search_path', 'health', false);


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
    WHERE conrelid = 'health.fees'::regclass
      AND conname = 'ux_fees_dedup'
  ) THEN
    ALTER TABLE health.fees
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

------------------------------ CREATE SCHEME FOR AIRQUALITY ------------------------------
Create schema if not exists airq;
SELECT set_config('search_path', 'airq', false);


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
-- CREATE TABLE IF NOT EXISTS station_daily (
--   station_daily_id  BIGSERIAL PRIMARY KEY,
--   station_id        INT NOT NULL REFERENCES stations(station_id) ON DELETE CASCADE,
--   pollutant_code    TEXT NOT NULL REFERENCES pollutants(code) ON DELETE RESTRICT,
--   date_utc          DATE NOT NULL,
--   agg_value         DOUBLE PRECISION,     -- z.B. Median oder Mittelwert des Tages
--   unit              TEXT,
--   method            TEXT DEFAULT 'median', -- 'median' | 'mean' etc.
--   dataset_id        INT REFERENCES datasets(dataset_id) ON DELETE SET NULL,
--   metadata          JSONB,
--   UNIQUE (station_id, pollutant_code, date_utc, method)
-- );

-- Sinnvolle Indizes für typische Abfragen
CREATE INDEX IF NOT EXISTS ix_station_measurements_station_ts
  ON station_measurements (station_id, ts_utc);
CREATE INDEX IF NOT EXISTS ix_station_measurements_pollutant_ts
  ON station_measurements (pollutant_code, ts_utc);
CREATE INDEX IF NOT EXISTS ix_station_measurements_ts
  ON station_measurements (ts_utc);

-- CREATE INDEX IF NOT EXISTS ix_station_daily_station_date
--   ON station_daily (station_id, date_utc);
-- CREATE INDEX IF NOT EXISTS ix_station_daily_pollutant_date
--   ON station_daily (pollutant_code, date_utc);


