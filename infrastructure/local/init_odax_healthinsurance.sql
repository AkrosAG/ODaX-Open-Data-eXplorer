-- Initialize ODaX health insurance schema and table(s) in PostgreSQL
-- Idempotent: will (re)create schema and tables if they do not exist

-- Create schema
CREATE SCHEMA IF NOT EXISTS odax;

-- Main premiums table
CREATE TABLE IF NOT EXISTS odax.healthinsurance_premiums (
    insurer_bag_code        text            NOT NULL,   -- e.g., "0008"
    canton                  text            NOT NULL,   -- e.g., "ZH"
    territory               text            NULL,       -- "Hoheitsgebiet" (e.g., CH)
    business_year           integer         NULL,       -- "Geschäftsjahr"
    survey_year             integer         NULL,       -- "Erhebungsjahr"
    fee_region              text            NULL,       -- "Region" (e.g., PR-REG CH0)
    age_class               text            NULL,       -- "Altersklasse" (AKL-KIN/JUG/ERW)
    accident_coverage       text            NULL,       -- "Unfalleinschluss" (MIT-UNF/OHN-UNF)
    tariff_code             text            NULL,       -- "Tarif" (e.g., 01_016, BASE)
    tariff_type             text            NULL,       -- "Tariftyp" (e.g., TAR-HAM, TAR-BASE)
    sub_age_group           text            NULL,       -- "Altersuntergruppe" (e.g., K1)
    franchise_level_code    text            NULL,       -- "Franchisestufe" (e.g., FRAST1)
    franchise_label         text            NULL,       -- "Franchise" (e.g., FRA-300)
    premium_chf             numeric(12,2)   NULL,       -- "Prämie"
    is_base_p               smallint        NULL,       -- "isBaseP" (0/1)
    is_base_f               smallint        NULL,       -- "isBaseF" (0/1)
    tariff_label            text            NULL        -- "Tarifbezeichnung"
);

-- Helper: a view with friendlier column names for BI tools (e.g., Superset)
CREATE OR REPLACE VIEW odax.v_healthinsurance_premiums AS
SELECT
    insurer_bag_code       AS insurer_bag_code,
    canton                 AS canton,
    territory              AS territory,
    business_year          AS business_year,
    survey_year            AS survey_year,
    fee_region             AS fee_region,
    age_class              AS age_class,
    accident_coverage      AS accident_coverage,
    tariff_code            AS tariff_code,
    tariff_type            AS tariff_type,
    sub_age_group          AS sub_age_group,
    franchise_level_code   AS franchise_level_code,
    franchise_label        AS franchise_label,
    premium_chf            AS premium_chf,
    is_base_p              AS is_base_p,
    is_base_f              AS is_base_f,
    tariff_label           AS tariff_label
FROM odax.healthinsurance_premiums;