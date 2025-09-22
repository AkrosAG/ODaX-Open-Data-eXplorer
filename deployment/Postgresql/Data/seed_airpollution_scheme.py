import os
import sys
import csv
import json
import unicodedata
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, List
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


HOST_PORT = os.getenv("HOST_PORT")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")

# ------------------------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------------------------
# Standard: lokaler Podman-Container aus dem Schema-Setup
PG_URL = os.environ.get(
    "PG_URL_AIR",
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:{HOST_PORT}/{POSTGRES_DB}",
)

# Daten-Dateien
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..","..", ".."))
DATA_DIR = os.path.join(BASE, "data")

PATH_STATIONS = os.path.join(DATA_DIR, "nabel", "stations.csv")
PATH_CO = os.path.join(
    DATA_DIR, "nabel", "historical_data", "CO.csv"
)  # Tagesmittelwerte CO

# Optional: Source-/Dataset-Metadaten (frei anpassbar)
SOURCE_NAME = "MeteoSwiss / NABEL / geo.admin.ch"
DATASET_NAME_CO = "CO Tagesmittelwerte (NABEL)"

# ------------------------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------------------------


def engine() -> Engine:
    return create_engine(PG_URL, future=True)


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def norm_name(s: str) -> str:
    """
    Normalisiert Stations-/Spaltennamen für fuzzy matching:
    - trim
    - Unicode-Diacritics entfernen
    - lower
    - typische Trenner angleichen
    """
    if s is None:
        return ""
    s2 = strip_accents(str(s)).lower().strip()
    # ersetze sonderzeichen/hyphen/sonder-laute konsistent
    for ch in ["–", "—", "−"]:
        s2 = s2.replace(ch, "-")
    s2 = s2.replace("_", " ").replace("-", " ").replace("/", " ")
    # mehrfach spaces -> single space
    s2 = " ".join(s2.split())
    return s2


def get_or_create_source(
    conn,
    name: str,
    description: Optional[str] = None,
    url: Optional[str] = None,
    license_: Optional[str] = None,
    raw_source_metadata: Optional[dict] = None,
) -> int:
    row = conn.execute(
        text("SELECT source_id FROM airq.sources WHERE name=:n LIMIT 1"),
        {"n": name},
    ).first()
    if row:
        return int(row[0])
    row = conn.execute(
        text(
            """
            INSERT INTO airq.sources (name, description, url, license, raw_source_metadata)
            VALUES (:name, :description, :url, :license, CAST(:raw_meta AS JSONB))
            RETURNING source_id
        """
        ),
        {
            "name": name,
            "description": description,
            "url": url,
            "license": license_,
            "raw_meta": (
                json.dumps(raw_source_metadata) if raw_source_metadata else None
            ),
        },
    ).first()
    return int(row[0])


def get_or_create_dataset(
    conn,
    source_id: int,
    name: str,
    description: Optional[str] = None,
    access_url: Optional[str] = None,
    update_timestamp: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> int:
    row = conn.execute(
        text("SELECT dataset_id FROM airq.datasets WHERE name=:n LIMIT 1"),
        {"n": name},
    ).first()
    if row:
        return int(row[0])
    row = conn.execute(
        text(
            """
            INSERT INTO airq.datasets
              (source_id, name, description, access_url, update_timestamp, metadata)
            VALUES
              (:source_id, :name, :description, :access_url, :update_ts, CAST(:meta AS JSONB))
            RETURNING dataset_id
        """
        ),
        {
            "source_id": source_id,
            "name": name,
            "description": description,
            "access_url": access_url,
            "update_ts": update_timestamp,
            "meta": json.dumps(metadata) if metadata else None,
        },
    ).first()
    return int(row[0])


def ensure_pollutants(conn, items: List[Tuple[str, str, str]]):
    """
    items: [(code, label, unit)]
    """
    for code, label, unit in items:
        conn.execute(
            text(
                """
                INSERT INTO airq.pollutants (code, label, unit)
                VALUES (:c, :l, :u)
                ON CONFLICT (code) DO UPDATE SET label=EXCLUDED.label, unit=EXCLUDED.unit
            """
            ),
            {"c": code, "l": label, "u": unit},
        )


def load_stations(conn) -> Dict[str, int]:
    """
    Lädt stations.csv in die Tabelle 'stations' (idempotent).
    Gibt Mapping normalisierter Stationsnamen -> station_id zurück.
    CSV-Spalten erwartet:
      Station, Tag (optional), Easting, Northing, Meters_Above_Sealevel, Locationtype, Remarks
    """
    if not os.path.exists(PATH_STATIONS):
        print(
            f"⚠️ stations.csv nicht gefunden unter {PATH_STATIONS} – überspringe Stations-Import."
        )
        return {}

    df = pd.read_csv(PATH_STATIONS)
    # Spalten robust ansprechen
    rename_map = {
        "Station": "name",
        "Tag": "short_code",
        "Easting": "lv95_easting",
        "Northing": "lv95_northing",
        "Meters_Above_Sealevel": "elevation_m",
        "Locationtype": "location_type",
        "Remarks": "remarks",
    }
    df = df.rename(columns=rename_map)

    name_to_id: Dict[str, int] = {}

    for _, r in df.iterrows():
        name = str(r.get("name") or "").strip()
        if not name:
            continue
        short_code = str(r.get("short_code") or "").strip() or None
        lv95_e = None
        lv95_n = None
        elev = None
        try:
            lv95_e = (
                float(r.get("lv95_easting"))
                if pd.notna(r.get("lv95_easting"))
                else None
            )
        except Exception:
            pass
        try:
            lv95_n = (
                float(r.get("lv95_northing"))
                if pd.notna(r.get("lv95_northing"))
                else None
            )
        except Exception:
            pass
        try:
            elev = (
                float(r.get("elevation_m")) if pd.notna(r.get("elevation_m")) else None
            )
        except Exception:
            pass

        location_type = str(r.get("location_type") or "").strip() or None
        remarks = str(r.get("remarks") or "").strip() or None

        # Upsert per external_id = name (du kannst hier auch separates external_id-Feld verwenden)
        row = conn.execute(
            text(
                """
                INSERT INTO airq.stations (external_id, short_code, name, lv95_easting, lv95_northing, elevation_m, location_type, remarks)
                VALUES (:eid, :sc, :nm, :e, :n, :el, :lt, :rm)
                ON CONFLICT (external_id) DO UPDATE SET
                  short_code=EXCLUDED.short_code,
                  name=EXCLUDED.name,
                  lv95_easting=EXCLUDED.lv95_easting,
                  lv95_northing=EXCLUDED.lv95_northing,
                  elevation_m=EXCLUDED.elevation_m,
                  location_type=EXCLUDED.location_type,
                  remarks=EXCLUDED.remarks
                RETURNING station_id
            """
            ),
            {
                "eid": name,  # external_id = Vollname aus CSV
                "sc": short_code,
                "nm": name,
                "e": lv95_e,
                "n": lv95_n,
                "el": elev,
                "lt": location_type,
                "rm": remarks,
            },
        ).first()
        station_id = int(row[0])
        name_to_id[norm_name(name)] = station_id

    return name_to_id


def parse_co_csv_header_and_rows(path: str):
    """
    Liest CO.csv mit Kopfbereich.
    Erwartet eine Zeile, die mit 'Datum/Zeit' beginnt; danach folgen Stationsspalten.
    Gibt (header_cols, rows_iter) zurück.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")
        header_cols = None
        data_rows = []
        for row in reader:
            if not row:
                continue
            if row[0].strip().lower().startswith("datum/zeit"):
                header_cols = row
                break
        if header_cols is None:
            raise RuntimeError("Headerzeile 'Datum/Zeit' nicht gefunden.")
        # Restliche Zeilen sind Daten
        for row in reader:
            if not row or all((c or "").strip() == "" for c in row):
                continue
            data_rows.append(row)
    return header_cols, data_rows


def ensure_station_lookup_for_header(
    station_name_map: Dict[str, int], header_cols: List[str]
) -> Dict[int, int]:
    """
    Erzeugt ein Mapping: Spaltenindex -> station_id
    """
    idx_to_station: Dict[int, int] = {}
    for idx, col in enumerate(header_cols):
        if idx == 0:
            continue  # Datum/Zeit
        key = norm_name(col)
        # Versuche exakten Normalisierungs-Match
        sid = station_name_map.get(key)
        if sid is not None:
            idx_to_station[idx] = sid
            continue
        # Fallback-Heuristik: entferne Bindestriche ' - ' Varianten
        key2 = key.replace("  ", " ")
        sid = station_name_map.get(key2)
        if sid is not None:
            idx_to_station[idx] = sid
            continue
        # Kein Treffer -> Spalte wird ignoriert
    return idx_to_station


def upsert_measurements_bulk(
    conn,
    rows: List[Tuple[int, str, datetime, float, str, Optional[int], Optional[dict]]],
):
    """
    rows: Liste von Tupeln (station_id, pollutant_code, ts_utc, value, unit, dataset_id, raw_meta)
    """
    if not rows:
        return 0
    dbapi_conn = conn.connection.driver_connection
    from psycopg2.extras import execute_values

    cols = [
        "station_id",
        "pollutant_code",
        "ts_utc",
        "value",
        "unit",
        "dataset_id",
        "raw_source_metadata",
    ]
    sql = f"""
        INSERT INTO airq.station_measurements ({', '.join(cols)})
        VALUES %s
        ON CONFLICT (station_id, pollutant_code, ts_utc)
        DO UPDATE SET
          value = EXCLUDED.value,
          unit = EXCLUDED.unit,
          dataset_id = COALESCE(EXCLUDED.dataset_id, airq.station_measurements.dataset_id),
          raw_source_metadata = COALESCE(EXCLUDED.raw_source_metadata, airq.station_measurements.raw_source_metadata)
    """

    def adapt_row(r):
        station_id, pol, ts, val, unit, dsid, meta = r
        return (
            station_id,
            pol,
            ts,
            val,
            unit,
            dsid,
            json.dumps(meta) if isinstance(meta, dict) else None,
        )

    with dbapi_conn.cursor() as cur:
        execute_values(
            cur,
            sql,
            [adapt_row(r) for r in rows],
            template="(%s,%s,%s,%s,%s,%s,%s)",
            page_size=5000,
        )


def seed_co(conn, station_name_map: Dict[str, int], dataset_id: int):
    """
    Lädt CO.csv Tagesmittelwerte in station_measurements (pollutant_code='CO').
    """
    if not os.path.exists(PATH_CO):
        print(f"⚠️ CO.csv nicht gefunden unter {PATH_CO} – überspringe CO-Import.")
        return

    header, data_rows = parse_co_csv_header_and_rows(PATH_CO)
    idx_to_station = ensure_station_lookup_for_header(station_name_map, header)

    # Einheit aus Kopfzeilen oberhalb: CO.csv enthält 'Einheit: mg/m3' – falls du die Einheit
    # programmatisch auslesen willst, kannst du sie hier übergeben; wir nutzen 'mg/m3'.
    unit = "mg/m3"
    pol_code = "CO"

    # Insert-Puffer
    buf: List[Tuple[int, str, datetime, float, str, Optional[int], Optional[dict]]] = []
    total = 0

    for row in data_rows:
        date_str = row[0].strip()
        # dd.mm.yyyy
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y").replace(tzinfo=timezone.utc)
        except Exception:
            # Versuche ISO yyyy-mm-dd
            try:
                dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            except Exception:
                continue

        for idx, sid in idx_to_station.items():
            if idx >= len(row):
                continue
            raw = (row[idx] or "").strip()
            if raw == "":
                continue
            # Dezimalpunkt/Komma robust
            v_str = raw.replace(",", ".")
            try:
                val = float(v_str)
            except Exception:
                continue

            meta = {"source_file": os.path.basename(PATH_CO), "col": header[idx]}
            buf.append((sid, pol_code, dt, val, unit, dataset_id, meta))
            if len(buf) >= 5000:
                upsert_measurements_bulk(conn, buf)
                total += len(buf)
                buf.clear()

    if buf:
        upsert_measurements_bulk(conn, buf)
        total += len(buf)

    print(f"✅ CO-Import abgeschlossen: {total} Messungen upserted.")


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------


def main():
    eng = engine()
    with eng.begin() as conn:
        # 1) Source/Dataset anlegen
        source_id = get_or_create_source(
            conn,
            name=SOURCE_NAME,
            description="Offene Luftqualitätsdaten (NABEL/geo.admin.ch/MeteoSwiss).",
            url="https://data.geo.admin.ch/",
            license_="Open use (gemäß Quelle)",
            raw_source_metadata={"created_by": "seed_air_quality.py"},
        )
        dataset_id_co = get_or_create_dataset(
            conn,
            source_id=source_id,
            name=DATASET_NAME_CO,
            description="Tagesmittelwerte Kohlenmonoxid (CO), Beispiel-Import.",
            access_url=os.path.basename(PATH_CO) if os.path.exists(PATH_CO) else None,
            update_timestamp=datetime.now(tz=timezone.utc),
            metadata={"format": {"type": "csv", "sep": ";", "encoding": "latin1"}},
        )

        # 2) Pollutanten absichern (falls Schema-Setup sie nicht bereits angelegt hat)
        ensure_pollutants(
            conn,
            [
                ("CO", "Kohlenmonoxid", "mg/m3"),
                ("NO2", "Stickstoffdioxid", "µg/m3"),
                ("PM10", "Feinstaub PM10", "µg/m3"),
                ("PM2_5", "Feinstaub PM2.5", "µg/m3"),
                ("O3", "Ozon", "µg/m3"),
            ],
        )

        # 3) Stationen laden
        station_name_map = load_stations(conn)  # normierter Name -> station_id
        if not station_name_map:
            print(
                "⚠️ Keine Stationen importiert – Messwert-Import könnte Spalten nicht zuordnen."
            )

        # 4) CO.csv importieren (idempotent via ON CONFLICT)
        seed_co(conn, station_name_map, dataset_id_co)

    print("🎉 Seeding abgeschlossen.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Fehler im Seeder: {e}")
        sys.exit(1)
