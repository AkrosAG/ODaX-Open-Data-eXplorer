-- \c postgres_db

-- CREATE SCHEMA IF NOT EXISTS public;


-- CREATE TABLE IF NOT EXISTS source (
--   id        SERIAL PRIMARY KEY,
--   title            TEXT NOT NULL,
--   summary          TEXT,
--   url              TEXT,
--   license          TEXT,
--   raw_source_metadata JSONB
-- );

-- CREATE TABLE IF NOT EXISTS dataset (
--   id       SERIAL PRIMARY KEY,
--   source_id        INT NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
--   title            TEXT NOT NULL,
--   summary          TEXT,
--   access_url       TEXT,
--   update_timestamp TIMESTAMP,
--   metadata         JSONB
-- );
-- Drop tables in reverse dependency order (child tables first)
DROP TABLE IF EXISTS pollutant_measurement;
DROP TABLE IF EXISTS pollutant;
DROP TABLE IF EXISTS station;

CREATE TABLE station (
  id               SERIAL PRIMARY KEY,         
  code             CHAR(3) NOT NULL,
  title            VARCHAR(100) NOT NULL,
  -- canton_code      CHAR(2),
  lv95_easting     NUMERIC(10,2),
  lv95_northing    NUMERIC(10,2),
  wgs84_lon        DOUBLE PRECISION,
  wgs84_lat        DOUBLE PRECISION,
  elevation        NUMERIC(8,2),
  location_type    TEXT,
  remarks          TEXT
);

CREATE TABLE pollutant (
  id   SERIAL PRIMARY KEY,
  code VARCHAR(20) NOT NULL,
  title VARCHAR(100) NOT NULL,
  unit VARCHAR(20)
);

CREATE TABLE pollutant_measurement (
  id                BIGSERIAL PRIMARY KEY,
  pollutant_id      INT NOT NULL REFERENCES pollutant(id) ON DELETE CASCADE,
  station_id        INT NOT NULL REFERENCES station(id) ON DELETE CASCADE,
  reading           DOUBLE PRECISION,
  created_at        DATE NOT NULL
);

-- Create indexes for pollutant_measurement table to improve query performance
CREATE INDEX IF NOT EXISTS ix_pollutant_measurement_station_date 
  ON pollutant_measurement (station_id, created_at);

CREATE INDEX IF NOT EXISTS ix_pollutant_measurement_pollutant_date 
  ON pollutant_measurement (pollutant_id, created_at);

CREATE INDEX IF NOT EXISTS ix_pollutant_measurement_date 
  ON pollutant_measurement (created_at);

CREATE INDEX IF NOT EXISTS ix_pollutant_measurement_station_pollutant 
  ON pollutant_measurement (station_id, pollutant_id);

CREATE INDEX IF NOT EXISTS ix_pollutant_measurement_reading 
  ON pollutant_measurement (reading) WHERE reading IS NOT NULL;






