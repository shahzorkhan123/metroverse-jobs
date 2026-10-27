"""Download the O*NET database and extract the job x task (DWA) list.

Downloads the O*NET database ZIP and writes data/raw/onet_job_dwa.csv:
one row per (6-digit SOC, Detailed Work Activity) pair.  O*NET-SOC detail
codes (XX-XXXX.YY) are collapsed to SOC (XX-XXXX) by taking the union of
their DWAs.

Job/Task complexity (wage-seeded JCI/TCI) needs OES wages, so it is
computed in compute_space.py, not here.

Usage:
    from scripts.pipeline.fetch_onet import fetch_and_extract
    zip_path, csv_path = fetch_and_extract()
"""

import csv
from pathlib import Path

import requests

from . import config

# O*NET database URL (29.3, the version used by compute_space)
ONET_DB_URL = f"{config.ONET_BASE_URL}/db_29_3_excel.zip"


def _download_zip(url: str, dest_dir: Path) -> Path:
    """Download a ZIP file and return the local path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    dest_path = dest_dir / filename

    if dest_path.exists():
        print(f"  Using cached: {dest_path.name}")
        return dest_path

    print(f"  Downloading: {url}")
    resp = requests.get(url, timeout=300,
                        headers={"User-Agent": "Mozilla/5.0 (metroverse-jobs)"})
    resp.raise_for_status()
    dest_path.write_bytes(resp.content)
    print(f"  Saved: {dest_path.name} ({len(resp.content):,} bytes)")
    return dest_path


def fetch_and_extract(onet_url: str | None = None,
                      raw_dir: Path | None = None) -> tuple[Path, Path]:
    """Download O*NET and write the job x DWA edge list.

    Returns (zip_path, csv_path); the CSV has columns
        soc_code, dwa_id, dwa_title
    """
    from .compute_space import load_onet_job_dwa

    if raw_dir is None:
        raw_dir = config.RAW_DIR
    if onet_url is None:
        onet_url = ONET_DB_URL

    print("Fetching O*NET database...")
    zip_path = _download_zip(onet_url, raw_dir)

    print("Reading Tasks to DWAs...")
    pairs, titles = load_onet_job_dwa(zip_path)
    print(f"  {len(pairs)} job-DWA pairs, "
          f"{len({j for j, _ in pairs})} jobs, {len(titles)} DWAs")

    csv_path = raw_dir / "onet_job_dwa.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["soc_code", "dwa_id", "dwa_title"])
        for soc, dwa in sorted(pairs):
            writer.writerow([soc, dwa, titles.get(dwa, "")])

    print(f"  Wrote: {csv_path.name}")
    return zip_path, csv_path
