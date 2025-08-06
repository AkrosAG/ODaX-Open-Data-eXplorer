"""
MeteoSwiss Station Data Downloader

This script downloads meteorological data from MeteoSwiss stations using the geo.admin.ch STAC API.
It fetches a list of all available stations and downloads their data files to a local directory.
The script skips files that have already been downloaded to avoid redundant downloads.
"""

import requests
import os
from typing import Dict, List, Any, Union
from loguru import logger

STAC_URL: str = (
    "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn/items"
)
OUTDIR: str = "meteoswiss_smn_data"
os.makedirs(OUTDIR, exist_ok=True)


def download_file(url: str, path: str) -> None:
    """
    Download a file from a URL and save it to the specified path.

    Parameters:
        url (str): The URL of the file to download
        path (str): The local path where the file will be saved

    Returns:
        None
    """
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


logger.info("📥 Fetching station list...")
resp: requests.Response = requests.get(STAC_URL, params={"limit": 200})
resp.raise_for_status()
features: List[Dict[str, Any]] = resp.json().get("features", [])

logger.info(f"Found {len(features)} stations. Starting download…")
for feat in features:
    props: Dict[str, Any] = feat["properties"]
    station: Union[str, int] = props.get("ogc_fid") or feat["id"]
    station_id: Union[str, Any] = props.get("station") or feat["assets"].keys()
    station_id = station_id if isinstance(station_id, str) else feat["id"]

    for asset_name, asset in feat["assets"].items():
        url: str = asset["href"]
        fname: str = f"{station_id}_{asset_name}.csv"
        outpath: str = os.path.join(OUTDIR, fname)
        if os.path.exists(outpath):
            logger.debug(f"Skipping {fname} (already exists).")
            continue
        logger.info(f"→ Downloading {asset_name} for station {station_id} …")
        download_file(url, outpath)

logger.success("✅ Download complete!")
