import requests
import os

STAC_URL = "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn/items"
OUTDIR = "meteoswiss_smn_data"
os.makedirs(OUTDIR, exist_ok=True)

def download_file(url, path):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

print("📥 Fetching station list...")
resp = requests.get(STAC_URL, params={"limit": 200})
resp.raise_for_status()
features = resp.json().get("features", [])

print(f"Found {len(features)} stations. Starting download…")
for feat in features:
    props = feat["properties"]
    station = props.get("ogc_fid") or feat["id"]
    station_id = props.get("station") or feat["assets"].keys()
    station_id = station_id if isinstance(station_id, str) else feat["id"]

    for asset_name, asset in feat["assets"].items():
        url = asset["href"]
        fname = f"{station_id}_{asset_name}.csv"
        outpath = os.path.join(OUTDIR, fname)
        if os.path.exists(outpath):
            continue  # skip already downloaded files
        print(f" → Downloading {asset_name} for {station_id} …")
        download_file(url, outpath)

print("✅ Download complete!")
