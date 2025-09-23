import os
import re
import json
import math
import pandas as pd
from typing import Any, Optional, Sequence, List
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.engine import Engine
import unicodedata
import hashlib
from datetime import datetime, timezone
from dotenv import load_dotenv

from imping.healthinsurance.lib_healthinsurance import (
    GetMunicipalities_PerCanton,
    GetMunicipalities_MultipleFeeRegions,
)

load_dotenv()

HOST_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")

# ── CONFIG ─────────────────────────────────────────────────────────────────────
PG_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{HOST_PORT}/{POSTGRES_DB}"

# Input files
# Determine project root relative to this file to avoid relying on CWD during debug runs
BASE = "/app/data/healthinsurance/"
CSV_FEES = os.path.join(BASE,"Prämien_CH.csv")
XSLX_FEES = os.path.join(BASE, "Prämien_CH.xlsx")

XLS_MUNIC = os.path.join(BASE,"praemienregionen-ab-2025.xlsx")
XLS_INSURERS = os.path.join(BASE,"BagNr_Mapping_KV.xlsx")

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
    md.reflect(eng, schema="health")


# Idempotent upsert helpers (PostgreSQL)
def upsert_canton(conn, code: str, name: str):
    conn.execute(
        text(
            """
        INSERT INTO health.cantons (canton_code, name)
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
        INSERT INTO health.fee_regions (canton_code, region_no)
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
        SELECT fee_region_id FROM health.fee_regions
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
        INSERT INTO health.municipalities (name, canton_code, fee_region_id)
        VALUES (:n, :c, :f)
        ON CONFLICT (name, canton_code) DO UPDATE SET fee_region_id = COALESCE(EXCLUDED.fee_region_id, health.municipalities.fee_region_id)
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
        SELECT municipality_id FROM health.municipalities
        WHERE name=:n AND canton_code=:c
    """
        ),
        {"n": name, "c": canton_code},
    ).scalar_one()


def upsert_insurer(conn, bag_number: int, name: str):
    conn.execute(
        text(
            """
        INSERT INTO health.insurers (bag_number, name)
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
        INSERT INTO health.{table} ({pkcol}, label)
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
        INSERT INTO health.franchises (amount)
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
        INSERT INTO health.fees (
          insurer_bag, canton_code, fee_region_id,
          age_class_code, age_subgroup_code, accident_included,
          franchise_amount, tariff_type_code, valid_from, valid_to,
          currency, monthly_premium, dataset_id, raw_source_metadata
        ) VALUES (
          :insurer_bag, :canton_code, :fee_region_id,
          :age_class_code, :age_subgroup_code, :accident_included,
          :franchise_amount, :tariff_type_code, :valid_from, :valid_to,
          :currency, :monthly_premium, :dataset_id, :raw_source_metadata
        )
        ON CONFLICT ON CONSTRAINT ux_fees_dedup
        DO UPDATE SET
          monthly_premium     = EXCLUDED.monthly_premium,
          raw_source_metadata = COALESCE(EXCLUDED.raw_source_metadata, health.fees.raw_source_metadata);
    """
        ),
        row,
    )


# High-throughput Bulk-Insert/Upsert für fees via psycopg2.execute_values
def insert_fees_bulk(conn, rows, batch_size: int = 5000):
    """
    Erwartet rows als Iterable[dict] mit den Spalten aus cols.
    Nutzt execute_values, um multi-VALUES + ON CONFLICT durchzuführen.
    """
    if not rows:
        return 0

    cols = [
        "insurer_bag",
        "canton_code",
        "fee_region_id",
        "age_class_code",
        "age_subgroup_code",
        "accident_included",
        "franchise_amount",
        "tariff_type_code",
        "tariff_name",
        "valid_from",
        "valid_to",
        "currency",
        "monthly_premium",
        "dataset_id",
        "raw_source_metadata",
    ]

    # Zugriff auf DBAPI-Connection (psycopg2)
    dbapi_conn = conn.connection.driver_connection  # SQLAlchemy 2.x
    from psycopg2.extras import execute_values

    # KORREKT: execute_values erwartet genau ein %s, das durch die komplette VALUES-Liste ersetzt wird.
    sql = (
        f"INSERT INTO health.fees ({', '.join(cols)}) VALUES %s ON CONFLICT DO NOTHING"
    )

    def row_tuple(r):
        return tuple(r.get(c) for c in cols)

    inserted = 0
    with dbapi_conn.cursor() as cur:
        batch = []
        for r in rows:
            batch.append(row_tuple(r))
            if len(batch) >= batch_size:
                execute_values(
                    cur, sql, batch, template=f"({', '.join(['%s']*len(cols))})"
                )
                batch.clear()
        if batch:
            execute_values(cur, sql, batch, template=f"({', '.join(['%s']*len(cols))})")
        inserted = (
            cur.rowcount
        )  # Hinweis: kann bei execute_values -1 sein und ist nur ein grober Indikator

    return inserted


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


def fill_fee_regions(conn, df):
    """
    Erwartet df mit vektorisiert gesetzten Spalten:
      df["Kanton"] -> bereits normalisiert (z.B. "ZH", "NW", ...)
      df["Region"] -> bereits als Zahl (Int64) extrahiert
    Schreibt (canton_code, region_no) in health.fee_regions (ON CONFLICT DO NOTHING)
    und liefert ein Mapping {(canton_code, region_no): fee_region_id}.
    """

    # 1) gültige Paare auswählen und deduplizieren (vektorisiert)
    df_fr = df.loc[
        df["Kanton"].notna() & df["Region"].notna(), ["Kanton", "Region"]
    ].assign(Kanton=lambda x: x["Kanton"].astype(str).str.strip())
    # nur gültige 2-Buchstaben-Codes
    df_fr = df_fr[df_fr["Kanton"].str.len() == 2]
    df_fr = df_fr.drop_duplicates()

    # in Python-Tupel für executemany umwandeln
    rows = [(c, int(r)) for c, r in df_fr.to_records(index=False)]
    if not rows:
        return {}

    # 2) Bulk-Insert mit Upsert
    conn.execute(
        text(
            """
            INSERT INTO health.fee_regions (canton_code, region_no)
            VALUES (:canton_code, :region_no)
            ON CONFLICT (canton_code, region_no) DO NOTHING
        """
        ),
        [{"canton_code": c, "region_no": r} for (c, r) in rows],
    )

    # 3) IDs zu allen Paaren in einem Rutsch nachladen (JOIN auf VALUES), ggf. in Chunks
    mapping = {}
    CHUNK = 1000
    for i in range(0, len(rows), CHUNK):
        chunk = rows[i : i + CHUNK]
        values_sql = []
        params = {}
        for j, (c, r) in enumerate(chunk):
            values_sql.append(f"(:c{j}, :r{j})")
            params[f"c{j}"] = c
            params[f"r{j}"] = r

        sql = f"""
            SELECT fr.fee_region_id, fr.canton_code, fr.region_no
            FROM health.fee_regions fr
            JOIN (VALUES {", ".join(values_sql)}) AS v(canton_code, region_no)
              ON fr.canton_code = v.canton_code AND fr.region_no = v.region_no
        """
        for row in conn.execute(text(sql), params):
            mapping[(row.canton_code, row.region_no)] = row.fee_region_id

    return mapping


from collections import Counter


def build_municipalities_from_fr_map(fr_map: dict[tuple[str, int], int], pth: str):
    """
    fr_map: { (canton_code, region_no): fee_region_id }
    Returns:
      muni_by_pair: { (canton_code, region_no): [municipality, ...] }
      muni_rows:    { (municipality, canton_code, fee_region_id), ... }  # for bulk upsert
    """
    pairs = set(fr_map.keys())
    counts = Counter(cc for (cc, _) in pairs)
    multi_cantons = {cc for cc, n in counts.items() if n > 1}
    single_cantons = set(counts) - multi_cantons

    # Map single canton -> its only region_no
    single_pair_by_canton = {cc: rn for (cc, rn) in pairs if counts[cc] == 1}

    muni_by_pair: dict[tuple[str, int], list[str]] = {}

    # 1) Single-region cantons: call once per canton
    single_muni_by_canton: dict[str, list[str]] = {}
    for cc in single_cantons:

        try:
            lst = GetMunicipalities_PerCanton(swiss_cantons_abbr_to_name[cc]) or []
        except Exception:
            lst = []
        clean = sorted({str(m).strip() for m in lst if m and str(m).strip()})
        single_muni_by_canton[cc] = clean

    for cc, rn in single_pair_by_canton.items():
        muni_by_pair[(cc, rn)] = single_muni_by_canton.get(cc, [])

    # 2) Multi-region cantons: call once per (canton, region_no)
    for cc, rn in pairs:
        if cc in multi_cantons:
            try:
                lst = GetMunicipalities_MultipleFeeRegions(pth, cc, str(rn)) or []
            except Exception:
                lst = []
            clean = sorted({str(m).strip() for m in lst if m and str(m).strip()})
            muni_by_pair[(cc, rn)] = clean

    # 3) Build rows for bulk upsert: (name, canton_code, fee_region_id)
    muni_rows = set()
    for (cc, rn), names in muni_by_pair.items():
        fr_id = fr_map.get((cc, rn))
        if fr_id is None:
            continue
        for name in names:
            muni_rows.add((name, cc, fr_id))

    return muni_by_pair, muni_rows


def load_municipalities_and_regions(conn):
    sheet = "Anhang EDI Ver. über die PR"
    # XLS laden und Spalten trimmen
    df_municipality = pd.read_excel(XLS_MUNIC, sheet_name=sheet, dtype=str)
    df_municipality = df_municipality.rename(columns=lambda c: str(c).strip())

    # CSV laden (kleiner Ausschnitt) und Spalten trimmen
    df = pd.read_csv(CSV_FEES, sep=";", encoding="latin1").rename(columns=str.strip)

    df = df.rename(columns=str.strip)

    df["Kanton"] = df["Kanton"].map(normalize_canton_strict)
    df["Region"] = df["Region"].map(parse_region_no)

    fr_map = fill_fee_regions(conn, df)
    muni_by_pair, muni_rows = build_municipalities_from_fr_map(fr_map, XLS_MUNIC)
    # bulk upsert
    conn.execute(
        text(
            """
             INSERT INTO health.municipalities (name, canton_code, fee_region_id)
             VALUES (:name, :canton_code, :fee_region_id) ON CONFLICT (name, canton_code) DO
             UPDATE
                 SET fee_region_id = COALESCE (EXCLUDED.fee_region_id, health.municipalities.fee_region_id)
             """
        ),
        [
            {"name": n, "canton_code": c, "fee_region_id": fid}
            for (n, c, fid) in muni_rows
        ],
    )


def _file_info(path: str) -> dict:
    """
    Liefert Datei-Metadaten (size, mtime, sha256).
    """
    stat = os.stat(path)
    size = stat.st_size
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    sha256 = h.hexdigest()
    return {"size_bytes": size, "modified_at": mtime, "sha256": sha256}


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
            INSERT INTO health.age_subgroups (code, label, age_class_code)
            VALUES (:c,:l,:p)
            ON CONFLICT (code) DO UPDATE SET label=EXCLUDED.label, age_class_code=EXCLUDED.age_class_code;
        """
            ),
            {"c": code, "l": label, "p": parent},
        )

    # Common franchise set (extend if needed)
    for amt in [0, 100, 200, 300, 400, 500, 600, 1000, 1500, 2000, 2500]:
        upsert_franchise(conn, amt)


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


# reverse map: full name -> code
name_to_code = {
    strip_accents(v).upper(): k for k, v in swiss_cantons_abbr_to_name.items()
}


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


def ensure_age_subgroup(conn, code: str | None) -> str | None:
    if not code:
        return None
    c = str(code).strip().upper()
    if re.fullmatch(r"K\d+", c):
        conn.execute(
            text(
                """
            INSERT INTO health.age_subgroups (code, label, age_class_code)
            VALUES (:c, :l, 'AKL-KIN')
            ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, age_class_code = EXCLUDED.age_class_code;
        """
            ),
            {"c": c, "l": f"Kinder {c}"},
        )
        return c
    # Keep as-is only if it already exists
    exists = conn.execute(
        text("SELECT 1 FROM health.age_subgroups WHERE code=:c"), {"c": c}
    ).first()
    return c if exists else None


def get_municipality_ids(
    conn,
    fee_region_id: int,
    canton_code: str,
) -> List[int]:
    result = conn.execute(
        text(
            """
            SELECT municipality_id
            FROM health.municipalities
            WHERE fee_region_id = :f
              AND canton_code = :c
            """
        ),
        {"f": fee_region_id, "c": canton_code},
    )

    rows = result.fetchall()
    return [row[0] for row in rows] if rows else []


def load_table_as_df(
    conn,
    table: str,
    schema: str = "health",
    columns: Optional[Sequence[str]] = None,
    where: Optional[str] = None,
    params: Optional[dict] = None,
):
    """
    Lädt eine Tabelle aus Postgres als pandas.DataFrame.

    Args:
        conn: SQLAlchemy Connection oder Engine.
        table: Tabellenname (ohne Schema).
        schema: Schema-Name (Default: "health").
        columns: Optionale Liste der Spaltennamen. Wenn None -> "*".
        where: Optionaler WHERE-Teil ohne das Wort "WHERE" (z.B. 'id > :min_id').
        params: Bind-Parameter für das WHERE (z.B. {'min_id': 10}).

    Returns:
        pd.DataFrame
    """
    # Spaltenauswahl
    if columns:
        col_sql = ", ".join([f'"{c}"' for c in columns])
    else:
        col_sql = "*"

    # Vollqualifizierter Tabellenname
    qualified = f'{schema}."{table}"' if schema else f'"{table}"'

    # SQL zusammenbauen
    sql = f"SELECT {col_sql} FROM {qualified}"
    if where:
        sql += f" WHERE {where}"

    return pd.read_sql(text(sql), con=conn, params=params)


def load_fees(conn):
    # Ermittele den Dataset-Eintrag für die aktuell geladene CSV (per access_url oder Name)
    ds_row = conn.execute(
        text(
            """
            SELECT dataset_id
            FROM health.datasets
            WHERE access_url = :a OR name = :n
            ORDER BY dataset_id DESC
            LIMIT 1
            """
        ),
        {
            "a": os.path.basename(CSV_FEES),
            "n": "Prämien CH CSV 2025",
        },
    ).first()
    dataset_id = int(ds_row[0]) if ds_row else None

    # CSV lesen
    df = pd.read_csv(CSV_FEES, sep=";", encoding="latin1").rename(columns=str.strip)
    # df1 = pd.read_excel(XSLX_FEES).rename(columns=str.strip)
    # Zielspalte für Prämie ermitteln
    premium_col = next(
        (
            c
            for c in [
                "Praemie",
                "Prämie",
                "Monatspraemie",
                "Monatsprämie",
                "Praemie_Monat",
                "Betrag",
                "Fee",
                "Preis",
            ]
            if c in df.columns
        ),
        None,
    )
    if not premium_col:
        raise RuntimeError("Premium column not found")

    # Leichtes Pre-Cleaning und Vektorisierung häufiger Schritte
    df["Kanton"] = df["Kanton"].map(normalize_canton_strict)
    df = df[df["Kanton"].notna()]

    # Region-Nummer vektorisieren
    df["Region"] = (
        df["Region"].astype(str).str.extract(r"(\d+)$").astype(float).astype("Int64")
    )
    df = df[df["Region"].notna()]

    # Franchise vektorisieren (robust gegenüber 'FRA-123')
    df["Franchise"] = (
        df["Franchise"]
        .astype(str)
        .str.extract(r"(\d+)$")[0]
        .astype(float)
        .astype("Int64")
    )
    df = df[df["Franchise"].notna()]

    # Altersklasse/Tariftyp prüfen
    df["Altersklasse"] = df["Altersklasse"].astype(str).str.strip()
    df["Tariftyp"] = df["Tariftyp"].astype(str).str.strip()
    df["Tarif"] = df["Tarif"].astype(str).str.strip()
    df = df[(df["Altersklasse"] != "") & (df["Tariftyp"] != "")]

    # Unfall inkl.
    df["Unfalleinschluss"] = (
        df["Unfalleinschluss"].astype(str).str.upper().eq("MIT-UNF")
    )

    # Prämie als float (Komma zu Punkt)
    df["Prämie"] = df[premium_col].astype(str).str.replace(",", ".", regex=False)
    df["Prämie"] = pd.to_numeric(df["Prämie"], errors="coerce")
    df = df[df["Prämie"].notna()]

    # Gültig ab / bis
    vf_series = df["GueltigAb"] if "GueltigAb" in df.columns else df.get("GültigAb")
    if vf_series is None:
        df["__vf"] = "2025-01-01"
    else:
        vf = vf_series.fillna("2025-01-01").astype(str)
        df["__vf"] = vf
    df["__vt"] = None

    # Altersuntergruppe sicherstellen (nur Codes wie K\d+)
    sub_raw = df.get("Altersuntergruppe")
    if sub_raw is not None:
        df["Altersuntergruppe"] = sub_raw.astype(str).str.strip().str.upper()
        df["Altersuntergruppe"] = df["Altersuntergruppe"].replace(
            {"": None, "NAN": None}
        )
    else:
        df["Altersuntergruppe"] = None

    # Einmalig alle fehlenden K-Subgroups anlegen
    need_sub = sorted({s for s in df["Altersuntergruppe"].dropna().unique()})
    if need_sub:
        conn.execute(
            text(
                """
                INSERT INTO health.age_subgroups (code, label, age_class_code)
                SELECT x.code, ('Kinder ' || x.code), 'AKL-KIN'
                FROM (VALUES """
                + ", ".join([f"(:c{i})" for i in range(len(need_sub))])
                + """) AS x(code)
                ON CONFLICT (code) DO UPDATE
                    SET label = EXCLUDED.label,
                        age_class_code = EXCLUDED.age_class_code
            """
            ),
            {f"c{i}": c for i, c in enumerate(need_sub)},
        )

    # Einmalig alle (Kanton, Region)-Kombinationen upserten
    pairs = sorted({(str(c), int(r)) for c, r in zip(df["Kanton"], df["Region"])})
    if pairs:
        # Bulk-Insert fee_regions (DO NOTHING)
        params = {}
        values_sql = []
        for i, (c, rn) in enumerate(pairs):
            params[f"c{i}"] = c
            params[f"r{i}"] = rn
            values_sql.append(f"(:c{i}, :r{i})")
        conn.execute(
            text(
                f"""
                INSERT INTO health.fee_regions (canton_code, region_no)
                VALUES {", ".join(values_sql)}
                ON CONFLICT (canton_code, region_no) DO NOTHING
            """
            ),
            params,
        )

        # Mapping zu IDs holen
        params = {}
        values_sql = []
        for i, (c, rn) in enumerate(pairs):
            params[f"c{i}"] = c
            params[f"r{i}"] = rn
            values_sql.append(f"(:c{i}, :r{i})")
        rows = conn.execute(
            text(
                f"""
                SELECT fr.canton_code, fr.region_no, fr.fee_region_id
                FROM health.fee_regions fr
                JOIN (VALUES {", ".join(values_sql)}) AS v(canton_code, region_no)
                  ON fr.canton_code = v.canton_code AND fr.region_no = v.region_no
            """
            ),
            params,
        ).fetchall()
        region_id_map = {(r[0], r[1]): int(r[2]) for r in rows}
    else:
        region_id_map = {}

    # Rows für Bulk-Insert vorbereiten
    def _safe_int(x):
        try:
            return int(x)
        except Exception:
            return None

    rows = []
    src_file = os.path.basename(CSV_FEES)
    for i, r in df.iterrows():
        canton_code = r["Kanton"]
        region_no = int(r["Region"])
        fee_region_id = region_id_map.get((canton_code, region_no))
        if not fee_region_id:
            continue  # sollte selten sein

        age_class_code = r["Altersklasse"] or None
        age_subgroup_code = (
            r["Altersuntergruppe"]
            if isinstance(r["Altersuntergruppe"], str) and r["Altersuntergruppe"]
            else None
        )

        accident_included = bool(r["Unfalleinschluss"])
        franchise_amount = int(r["Franchise"])
        tariff_type_code = r["Tariftyp"] or None
        tariff_name = r["Tarif"] or None
        premium = float(r["Prämie"])
        insurer_bag = _safe_int(r.get("Versicherer"))

        if insurer_bag is None:
            continue

        row = {
            "insurer_bag": insurer_bag,
            "canton_code": canton_code,
            "fee_region_id": fee_region_id,
            "age_class_code": age_class_code,
            "age_subgroup_code": age_subgroup_code,
            "accident_included": accident_included,
            "franchise_amount": franchise_amount,
            "tariff_type_code": tariff_type_code,
            "tariff_name": tariff_name,
            "valid_from": r["__vf"],
            "valid_to": r["__vt"],
            "currency": "CHF",
            "monthly_premium": premium,
            "dataset_id": dataset_id,
            "raw_source_metadata": json.dumps(
                {"row_idx": int(i), "source_file": src_file}
            ),
        }
        rows.append(row)

    insert_fees_bulk(conn, rows, batch_size=5000)


def _json_or_none(d: Optional[dict]) -> Optional[str]:
    return json.dumps(d) if d is not None else None


def get_or_create_dataset(
    conn,
    source_id: int,
    name: str,
    description: Optional[str] = None,
    access_url: Optional[str] = None,
    update_timestamp: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> int:
    """
    Idempotent: sucht Dataset per name, erzeugt sonst und gibt dataset_id zurück.
    """
    existing = _select_id_by_name(conn, "datasets", "dataset_id", name)
    if existing:
        return existing

    row = conn.execute(
        text(
            """
            INSERT INTO health.datasets
              (source_id, name, description, access_url, update_timestamp, metadata)
            VALUES
              (:source_id, :name, :description, :access_url, :update_ts, CAST(:meta AS JSONB))
            RETURNING dataset_id;
            """
        ),
        {
            "source_id": source_id,
            "name": name,
            "description": description,
            "access_url": access_url,
            "update_ts": update_timestamp,
            "meta": _json_or_none(metadata),
        },
    ).first()
    return int(row[0])


def _select_id_by_name(conn, table: str, id_col: str, name: str) -> Optional[int]:
    row = conn.execute(
        text(f"SELECT {id_col} FROM health.{table} WHERE name = :n LIMIT 1"),
        {"n": name},
    ).first()
    return int(row[0]) if row else None


def get_or_create_source(
    conn,
    name: str,
    description: Optional[str] = None,
    url: Optional[str] = None,
    license_: Optional[str] = None,
    raw_source_metadata: Optional[dict] = None,
) -> int:
    """
    Idempotent: sucht Source per name, erzeugt sonst und gibt source_id zurück.
    """
    existing = _select_id_by_name(conn, "sources", "source_id", name)
    if existing:
        return existing

    row = conn.execute(
        text(
            """
            INSERT INTO health.sources (name, description, url, license, raw_source_metadata)
            VALUES (:name, :description, :url, :license, CAST(:raw_meta AS JSONB))
            RETURNING source_id;
            """
        ),
        {
            "name": name,
            "description": description,
            "url": url,
            "license": license_,
            "raw_meta": _json_or_none(raw_source_metadata),
        },
    ).first()
    return int(row[0])


def seed_sources_and_datasets(conn):
    """
    Legt eine Quelle (BAG) und drei zugehörige Datensätze an (CSV Prämien, XLSX Regionen, XLSX Versicherer-Mapping).
    Idempotent pro 'name'.
    """
    # Quelle
    source_meta = {
        "maintainer": "Bundesamt für Gesundheit (BAG)",
        "contact": None,
    }
    source_id = get_or_create_source(
        conn,
        name="BAG – Krankenversicherung",
        description="Offizielle Datengrundlagen zu Prämien, Regionen und Versicherern.",
        url="https://www.bag.admin.ch/",
        license_="Open use, ggf. BAG-Hinweise beachten",
        raw_source_metadata=source_meta,
    )

    # Datensätze inkl. Datei-Metadaten (falls vorhanden)
    datasets_to_seed = []

    if CSV_FEES and os.path.exists(CSV_FEES):
        fi = _file_info(CSV_FEES)
        datasets_to_seed.append(
            dict(
                name="Prämien CH CSV 2025",
                description="Monatsprämien Grundversicherung (CSV).",
                access_url=os.path.basename(CSV_FEES),
                update_timestamp=fi["modified_at"],
                metadata={
                    "file": {
                        "path": CSV_FEES,
                        "size_bytes": fi["size_bytes"],
                        "sha256": fi["sha256"],
                    },
                    "format": {"type": "csv", "sep": ";", "encoding": "latin1"},
                },
            )
        )

    if XLS_MUNIC and os.path.exists(XLS_MUNIC):
        fi = _file_info(XLS_MUNIC)
        datasets_to_seed.append(
            dict(
                name="Prämienregionen ab 2025 (XLSX)",
                description="Mapping Kantone/Regionen/Gemeinden.",
                access_url=os.path.basename(XLS_MUNIC),
                update_timestamp=fi["modified_at"],
                metadata={
                    "file": {
                        "path": XLS_MUNIC,
                        "size_bytes": fi["size_bytes"],
                        "sha256": fi["sha256"],
                    },
                    "format": {"type": "xlsx", "sheet": "Anhang EDI Ver. über die PR"},
                },
            )
        )

    if XLS_INSURERS and os.path.exists(XLS_INSURERS):
        fi = _file_info(XLS_INSURERS)
        datasets_to_seed.append(
            dict(
                name="BAG Versicherer Mapping (XLSX)",
                description="BAG-Nummer zu Krankenversicherer-Name.",
                access_url=os.path.basename(XLS_INSURERS),
                update_timestamp=fi["modified_at"],
                metadata={
                    "file": {
                        "path": XLS_INSURERS,
                        "size_bytes": fi["size_bytes"],
                        "sha256": fi["sha256"],
                    },
                    "format": {
                        "type": "xlsx",
                        "sheets": [
                            "Zugelassene Krankenversicherer",
                            "zugelassene krankenversicherer",
                        ],
                    },
                },
            )
        )

    # Anlegen (idempotent per name)
    for ds in datasets_to_seed:
        get_or_create_dataset(
            conn,
            source_id=source_id,
            name=ds["name"],
            description=ds.get("description"),
            access_url=ds.get("access_url"),
            update_timestamp=ds.get("update_timestamp"),
            metadata=ds.get("metadata"),
        )


def main():
    eng = engine()
    md = MetaData()
    with eng.begin() as conn:
        reflect(md, eng)

        seed_sources_and_datasets(conn)

        load_cantons(conn)
        seed_lookups(conn)
        load_insurers(conn)
        load_municipalities_and_regions(conn)

        load_fees(conn)

    print("✅ Load complete.")


main()
