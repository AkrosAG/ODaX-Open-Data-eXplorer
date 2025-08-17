import os
import re
import json
import math
import pandas as pd
from typing import Any, Optional
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.engine import Engine

# ── CONFIG ─────────────────────────────────────────────────────────────────────
PG_URL = "postgresql+psycopg2://postgres:odax123@localhost:5433/odax_test"

# Input files
# Determine project root relative to this file to avoid relying on CWD during debug runs
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
    f=3


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
    return int(m.group(1))


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
        ("K3", "1 Geschwister", "AKL-KIN"),
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


import unicodedata
CANTON_ALIASES = {
    "ZE": "ZG",      # ← change/remove if your file means something else
    "ZUERICH": "ZH",
    "ZURICH": "ZH",
    "GENEVE": "GE",
    "GENF": "GE",
}

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

# reverse map: full name -> code
name_to_code = {strip_accents(v).upper(): k for k, v in swiss_cantons_abbr_to_name.items()}

def normalize_canton_strict(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    u = s.upper()

    # exact 2-letter code
    if len(u) == 2 and u in swiss_cantons_abbr_to_name:
        return u

    # alias by code-ish tokens
    if u in CANTON_ALIASES:
        return CANTON_ALIASES[u]

    # try full name (accent-stripped)
    key = strip_accents(s).upper()
    return name_to_code.get(key)  # may be None


def ensure_age_subgroup(conn, code: str | None) -> str | None:
    if not code:
        return None
    c = str(code).strip().upper()
    if re.fullmatch(r"K\d+", c):
        conn.execute(text("""
            INSERT INTO public.age_subgroups (code, label, age_class_code)
            VALUES (:c, :l, 'AKL-KIN')
            ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, age_class_code = EXCLUDED.age_class_code;
        """), {"c": c, "l": f"Kinder {c}"})
        return c
    # Keep as-is only if it already exists
    exists = conn.execute(text("SELECT 1 FROM public.age_subgroups WHERE code=:c"), {"c": c}).first()
    return c if exists else None


def load_fees(conn):
    df = pd.read_csv(CSV_FEES, sep=";", encoding="latin1").rename(columns=str.strip)
    premium_col = next((c for c in ["Praemie","Prämie","Monatspraemie","Monatsprämie",
                                    "Praemie_Monat","Betrag","Fee","Preis"] if c in df.columns), None)
    if not premium_col:
        raise RuntimeError("Premium column not found")

    # Optional: quick pre-scan to warn about bad cantons
    bad = sorted({str(v) for v in df["Kanton"].dropna().unique()
                  if not normalize_canton_strict(v)})
    if bad:
        print("[WARN] Unbekannte Kantonseinträge im CSV:", bad)

    for i, r in df.iterrows():
        # Validate/normalize *before* we touch the DB
        canton_code = normalize_canton_strict(r.get("Kanton"))
        if not canton_code:
            print(f"[SKIP] Row {i}: invalid canton '{r.get('Kanton')}'")
            continue

        region_no = parse_region_no(r.get("Region"))
        if region_no is None:
            print(f"[SKIP] Row {i}: invalid region '{r.get('Region')}'")
            continue

        age_class_code = (str(r.get("Altersklasse") or "").strip() or None)
        if not age_class_code:
            print(f"[SKIP] Row {i}: missing Altersklasse")
            continue

        age_subgroup_code = ensure_age_subgroup(conn, str(r.get("Altersuntergruppe") or "").strip() or None)
        accident_included = parse_accident_included(r.get("Unfalleinschluss", ""))
        franchise_amount = parse_franchise_amount(r.get("Franchise"))
        if franchise_amount is None:
            print(f"[SKIP] Row {i}: invalid Franchise '{r.get('Franchise')}'")
            continue

        tariff_type_code = (str(r.get("Tariftyp") or "").strip() or None)
        if not tariff_type_code:
            print(f"[SKIP] Row {i}: missing Tariftyp")
            continue

        try:
            premium = float(str(r.get(premium_col)).replace(",", "."))
        except Exception:
            print(f"[SKIP] Row {i}: invalid premium '{r.get(premium_col)}'")
            continue

        vf = str(r.get("GueltigAb") or r.get("GültigAb") or "2025-01-01")
        vt = None

        # One savepoint per row
        try:
            with conn.begin_nested():  # -> SAVEPOINT
                fee_region_id = upsert_fee_region(conn, canton_code, region_no)
                # (Optionally ensure insurer exists; else skip)
                insurer_bag = int(r.get("Versicherer"))
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
                    "raw_source_metadata": json.dumps({"row_idx": int(i),
                                                       "source_file": os.path.basename(CSV_FEES)}),
                }
                insert_fee(conn, row)  # uses ON CONFLICT ON CONSTRAINT ux_fees_dedup
        except IntegrityError as e:
            # Rolls back to the SAVEPOINT automatically when exiting the with-block
            print(f"[SKIP] Row {i}: integrity error -> {e.orig.diag.message_primary}")
            continue
        except DataError as e:
            print(f"[SKIP] Row {i}: data error -> {e}")
            continue

def main():
    eng = engine()
    md = MetaData()
    with eng.begin() as conn:  # single outer transaction; commit once at end
        reflect(md, eng)
        '''
        load_cantons(conn)
        seed_lookups(conn)
        load_insurers(conn)
        load_municipalities_and_regions(conn)
        '''
        load_fees(conn)  # uses per-row savepoints
    print("✅ Load complete.")

if __name__ == "__main__":
    main()
