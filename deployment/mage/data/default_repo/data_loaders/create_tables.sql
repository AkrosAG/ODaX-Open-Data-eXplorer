-- Create the tables for the part healthinsurance in the schema public

DROP TABLE IF EXISTS fees;
DROP TABLE IF EXISTS municipalities;
DROP TABLE IF EXISTS fee_regions;
DROP TABLE IF EXISTS cantons;
DROP TABLE IF EXISTS insurers;
DROP TABLE IF EXISTS tariff_types;
DROP TABLE IF EXISTS age_subgroups;
DROP TABLE IF EXISTS age_classes;
DROP TABLE IF EXISTS franchises;

CREATE TABLE IF NOT EXISTS cantons (
  canton_code  CHAR(2) PRIMARY KEY,
  canton          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fee_regions (
  fee_region_id SERIAL PRIMARY KEY,
  canton_code   CHAR(2) NOT NULL REFERENCES cantons(canton_code) ON DELETE RESTRICT,
  region_no     SMALLINT NOT NULL,
  UNIQUE (canton_code, region_no)
);

CREATE TABLE IF NOT EXISTS municipalities (
  municipality_id SERIAL PRIMARY KEY,
  municipality    TEXT NOT NULL,
  canton_code     CHAR(2) NOT NULL REFERENCES cantons(canton_code) ON DELETE RESTRICT,
  fee_region_id   INT REFERENCES fee_regions(fee_region_id) ON DELETE SET NULL,
  UNIQUE (municipality, canton_code)
);

CREATE TABLE IF NOT EXISTS insurers (
  bag_number  INT PRIMARY KEY,
  insurer TEXT NOT NULL
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
  raw_source_metadata JSONB
);

ALTER TABLE fees
ADD CONSTRAINT ux_fees_dedup UNIQUE (
  insurer_bag, canton_code, fee_region_id,
  age_class_code, age_subgroup_code, accident_included,
  franchise_amount, tariff_type_code, valid_from, tariff_name
);


-- Indexes
CREATE INDEX IF NOT EXISTS idx_fees_lookup
  ON fees (canton_code, fee_region_id, age_class_code, accident_included, franchise_amount, tariff_type_code, tariff_name);

CREATE INDEX IF NOT EXISTS idx_fees_insurer
  ON fees (insurer_bag);

