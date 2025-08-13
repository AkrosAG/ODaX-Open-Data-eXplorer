import os
import re
import json
import math
import pandas as pd
from typing import Any, Optional

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.engine import Engine

# ── CONFIG ─────────────────────────────────────────────────────────────────────
PG_URL = "postgresql+psycopg2://postgres:odax123@localhost:5433/odax_test"

# Input files
BASE = os.getcwd()
CSV_FEES = os.path.join(BASE, "data", "healthinsurance", "Prämien_CH.csv")
XLS_MUNIC = os.path.join(
    BASE, "data", "healthinsurance", "praemienregionen-ab-2025.xlsx"
)
XLS_INSURERS = os.path.join(BASE, "data", "healthinsurance", "BagNr_Mapping_KV.xlsx")

# Canton dictionary (from your notebook)
swiss_cantons_abbr_to_name = {
    "AG": "Aargau",
    "AR": "Appenzell Ausserrhoden",
    "AI": "Appenzell Innerrhoden",
    "BL": "Basel-Landschaft",
    "BS": "Basel-Stadt",
    "BE": "Bern",
    "FR": "Freiburg",
    "GE": "Genf",
    "GL": "Glarus",
    "GR": "Graubünden",
    "JU": "Jura",
    "LU": "Luzern",
    "NE": "Neuenburg",
    "NW": "Nidwalden",
    "OW": "Obwalden",
    "SH": "Schaffhausen",
    "SZ": "Schwyz",
    "SO": "Solothurn",
    "SG": "St. Gallen",
    "TI": "Tessin",
    "TG": "Thurgau",
    "UR": "Uri",
    "VD": "Waadt",
    "VS": "Wallis",
    "ZG": "Zug",
    "ZH": "Zürich",
}


# ── DB helpers ─────────────────────────────────────────────────────────────────
def engine() -> Engine:
    return create_engine(PG_URL, future=True)


def reflect(md: MetaData, eng: Engine):
    md.clear()
    md.reflect(eng, schema="public")


# Idempotent upsert helpers (PostgreSQL)
def upsert_canton(conn, code: str, name: str):
    conn.execute(
        text(
            """
        INSERT INTO public.cantons (canton_code, name)
        VALUES (:code, :name)
        ON CONFLICT (canton_code) DO UPDATE SET name = EXCLUDED.name;
    """
        ),
        {"code": code, "name": name},
    )


def upsert_fee_region(conn, canton_code: str, region_no: int) -> int:
    # returns fee_region_id
    row = conn.execute(
        text(
            """
        INSERT INTO public.fee_regions (canton_code, region_no)
        VALUES (:c, :r)
        ON CONFLICT (canton_code, region_no) DO UPDATE SET region_no = EXCLUDED.region_no
        RETURNING fee_region_id;
    """
        ),
        {"c": canton_code, "r": region_no},
    ).first()
    if row:
        return row[0]
    # fallback lookup
    return conn.execute(
        text(
            """
        SELECT fee_region_id FROM public.fee_regions
        WHERE canton_code=:c AND region_no=:r
    """
        ),
        {"c": canton_code, "r": region_no},
    ).scalar_one()


def upsert_municipality(
    conn, name: str, canton_code: str, fee_region_id: Optional[int]
) -> int:
    row = conn.execute(
        text(
            """
        INSERT INTO public.municipalities (name, canton_code, fee_region_id)
        VALUES (:n, :c, :f)
        ON CONFLICT (name, canton_code) DO UPDATE SET fee_region_id = COALESCE(EXCLUDED.fee_region_id, public.municipalities.fee_region_id)
        RETURNING municipality_id;
    """
        ),
        {"n": name, "c": canton_code, "f": fee_region_id},
    ).first()
    if row:
        return row[0]
    return conn.execute(
        text(
            """
        SELECT municipality_id FROM public.municipalities
        WHERE name=:n AND canton_code=:c
    """
        ),
        {"n": name, "c": canton_code},
    ).scalar_one()


def upsert_insurer(conn, bag_number: int, name: str):
    conn.execute(
        text(
            """
        INSERT INTO public.insurers (bag_number, name)
        VALUES (:b, :n)
        ON CONFLICT (bag_number) DO UPDATE SET name = EXCLUDED.name;
    """
        ),
        {"b": bag_number, "n": name},
    )


def upsert_lookup(conn, table: str, pkcol: str, code: str, label: Optional[str] = None):
    if label is None:
        label = code
    conn.execute(
        text(
            f"""
        INSERT INTO public.{table} ({pkcol}, label)
        VALUES (:c, :l)
        ON CONFLICT ({pkcol}) DO UPDATE SET label = EXCLUDED.label;
    """
        ),
        {"c": code, "l": label},
    )


def upsert_franchise(conn, amount: int):
    conn.execute(
        text(
            """
        INSERT INTO public.franchises (amount)
        VALUES (:a)
        ON CONFLICT (amount) DO NOTHING;
    """
        ),
        {"a": amount},
    )


# Fees insert


def insert_fee(conn, row):
    conn.execute(
        text(
            """
        INSERT INTO public.fees (
          insurer_bag, canton_code, fee_region_id, municipality_id,
          age_class_code, age_subgroup_code, accident_included,
          franchise_amount, tariff_type_code, valid_from, valid_to,
          currency, monthly_premium, dataset_id, raw_source_metadata
        ) VALUES (
          :insurer_bag, :canton_code, :fee_region_id, :municipality_id,
          :age_class_code, :age_subgroup_code, :accident_included,
          :franchise_amount, :tariff_type_code, :valid_from, :valid_to,
          :currency, :monthly_premium, :dataset_id, :raw_source_metadata
        )
        ON CONFLICT ON CONSTRAINT ux_fees_dedup
        DO UPDATE SET
          monthly_premium     = EXCLUDED.monthly_premium,
          raw_source_metadata = COALESCE(EXCLUDED.raw_source_metadata, public.fees.raw_source_metadata);
    """
        ),
        row,
    )


# ── Parsing helpers ────────────────────────────────────────────────────────────
REGION_RX = re.compile(r"(\d+)$")  # e.g., "PR-REG CH1" -> 1
FRANCHISE_RX = re.compile(r"(\d+)$")  # e.g., "FRA-300"  -> 300


def parse_region_no(region: str) -> Optional[int]:
    if region is None or (isinstance(region, float) and math.isnan(region)):
        return None
    s = str(region).strip()
    m = REGION_RX.search(s)
    return int(m.group(1)) if m else None


def parse_franchise_amount(fr: Any) -> Optional[int]:
    if fr is None:
        return None
    s = str(fr).strip()
    if s.isdigit():
        return int(s)
    m = FRANCHISE_RX.search(s)
    return int(m.group(1)) if m else None


def parse_accident_included(val: str) -> bool:
    # Your data uses "MIT-UNF" vs "OHN-UNF"
    s = (val or "").strip().upper()
    return s == "MIT-UNF"


def normalize_canton(code: str) -> str:
    return (code or "").strip().upper()


# ── Loaders ────────────────────────────────────────────────────────────────────
def load_cantons(conn):
    for code, name in swiss_cantons_abbr_to_name.items():
        upsert_canton(conn, code, name)


def load_municipalities_and_regions(conn):
    sheet = "Anhang EDI Ver. über die PR"
    df = pd.read_excel(XLS_MUNIC, sheet_name=sheet)
    # Expecting columns: Kanton (abbr), Region (int or string), Gemeinde (name)
    df = df.rename(columns=str.strip)
    for _, r in df.iterrows():
        canton = normalize_canton(r["Kanton"])
        region_no = parse_region_no(r["Region"])
        gemeinde = str(r["Gemeinde"]).strip()
        if not canton or not region_no or not gemeinde:
            continue
        fr_id = upsert_fee_region(conn, canton, region_no)
        upsert_municipality(conn, gemeinde, canton, fr_id)


def load_insurers(conn):
    # Try common sheet names; your function already does similar
    for sheet in ["Zugelassene Krankenversicherer", "zugelassene krankenversicherer"]:
        try:
            df = pd.read_excel(XLS_INSURERS, sheet_name=sheet)
            df = df.rename(columns=str.strip)
            if "Nummer" in df.columns and "Name" in df.columns:
                for _, r in df.iterrows():
                    try:
                        bag = int(r["Nummer"])
                    except Exception:
                        continue
                    name = str(r["Name"]).strip()
                    if not name:
                        continue
                    upsert_insurer(conn, bag, name)
            break
        except Exception:
            continue


def seed_lookups(conn):
    # Tariff types (from your notebook)
    for code, label in [
        ("TAR-BASE", "Grundversicherung"),
        ("TAR-DIV", "Telmed/Div."),
        ("TAR-HMO", "HMO"),
        ("TAR-HAM", "Hausarztmodell"),
    ]:
        upsert_lookup(conn, "tariff_types", "code", code, label)

    # Age classes
    for code, label in [
        ("AKL-KIN", "Kinder"),
        ("AKL-JUG", "Jugendliche"),
        ("AKL-ERW", "Erwachsene"),
    ]:
        upsert_lookup(conn, "age_classes", "code", code, label)

    # Subgroups (examples; add the ones you actually use, like K1/K4/K5)
    for code, label, parent in [
        ("K1", "Einzelkind", "AKL-KIN"),
        ("K4", "1 Geschwister", "AKL-KIN"),
        ("K5", "2+ Geschwister", "AKL-KIN"),
    ]:
        conn.execute(
            text(
                """
            INSERT INTO public.age_subgroups (code, label, age_class_code)
            VALUES (:c,:l,:p)
            ON CONFLICT (code) DO UPDATE SET label=EXCLUDED.label, age_class_code=EXCLUDED.age_class_code;
        """
            ),
            {"c": code, "l": label, "p": parent},
        )

    # Common franchise set (extend if needed)
    for amt in [0, 100, 200, 300, 400, 500, 600, 1000, 1500, 2000, 2500]:
        upsert_franchise(conn, amt)


def load_fees(conn):
    # Your CSV: latin-1, semicolon
    df = pd.read_csv(CSV_FEES, sep=";", encoding="latin1")
    df = df.rename(columns=str.strip)

    # Expected columns (from your functions/notebook):
    # 'Kanton','Region','Versicherer','Unfalleinschluss','Altersklasse','Altersuntergruppe','Franchise','Tariftyp'
    # plus a premium column (guessing names - adjust as needed)
    # Try to detect a premium column:
    premium_col = None
    for cand in [
        "Praemie",
        "Prämie",
        "Monatspraemie",
        "Monatsprämie",
        "Praemie_Monat",
        "Betrag",
        "Fee",
        "Preis",
    ]:
        if cand in df.columns:
            premium_col = cand
            break
    if premium_col is None:
        raise RuntimeError(
            "Could not find premium column in CSV. Please adjust `premium_col` detection."
        )

    # Optional validity info if present; else default
    valid_from = None
    if "GueltigAb" in df.columns:
        valid_from = "GueltigAb"
    elif "GültigAb" in df.columns:
        valid_from = "GültigAb"

    # Row-wise insert
    for _, r in df.iterrows():
        canton_code = normalize_canton(r.get("Kanton", ""))
        if not canton_code:
            continue

        region_no = parse_region_no(r.get("Region"))
        if region_no is None:
            # some datasets store region as pure int already
            try:
                region_no = int(r.get("Region"))
            except Exception:
                continue

        # Ensure fee_region exists; municipality_id is optional (None)
        fee_region_id = upsert_fee_region(conn, canton_code, region_no)

        # Insurer BAG number
        try:
            insurer_bag = int(r.get("Versicherer"))
        except Exception:
            continue  # skip rows with invalid insurer id

        # Accident flag
        accident_included = parse_accident_included(r.get("Unfalleinschluss", ""))

        # Age class & subgroup
        age_class_code = str(r.get("Altersklasse", "")).strip() or None
        age_subgroup_code = str(r.get("Altersuntergruppe", "")).strip() or None
        if age_subgroup_code in ["nan", "None", ""]:
            age_subgroup_code = None

        # Franchise as integer
        franchise_amount = parse_franchise_amount(r.get("Franchise"))
        if franchise_amount is None:
            continue

        # Tariff type code
        tariff_type_code = str(r.get("Tariftyp", "")).strip() or None
        if tariff_type_code is None:
            continue

        # Premium
        try:
            premium = float(str(r.get(premium_col)).replace(",", "."))
        except Exception:
            continue

        # Validity
        vf = str(r.get(valid_from)) if valid_from else "2025-01-01"
        vt = None

        row = {
            "insurer_bag": insurer_bag,
            "canton_code": canton_code,
            "fee_region_id": fee_region_id,
            "municipality_id": None,
            "age_class_code": age_class_code,
            "age_subgroup_code": age_subgroup_code,
            "accident_included": accident_included,
            "franchise_amount": franchise_amount,
            "tariff_type_code": tariff_type_code,
            "valid_from": vf,
            "valid_to": vt,
            "currency": "CHF",
            "monthly_premium": premium,
            "dataset_id": None,
            "raw_source_metadata": json.dumps(
                {"row_idx": int(_), "source_file": os.path.basename(CSV_FEES)}
            ),
        }
        insert_fee(conn, row)


def main():
    eng = engine()
    md = MetaData()
    with eng.begin() as conn:
        # reflect once to ensure schema exists (optional but fine)
        reflect(md, eng)

        # Seed lookups & reference data
        load_cantons(conn)
        seed_lookups(conn)
        load_insurers(conn)
        load_municipalities_and_regions(conn)

        # Load fees
        load_fees(conn)

    print("✅ Load complete.")


if __name__ == "__main__":
    main()
