"""Download BLS OES bulk data files and parse into a combined CSV.

BLS Occupational Employment and Wage Statistics (OES) data comes as
ZIP files containing Excel workbooks. We download national, state,
and metro area files, filter to cross-industry detailed occupations,
and produce a single combined CSV ready for import into SQLite.

Usage:
    from scripts.pipeline.fetch_bls import fetch_and_parse
    csv_path = fetch_and_parse(year=2024)
"""

import csv
import io
import zipfile
from pathlib import Path

import requests

from . import config

# BLS OES URL patterns (YY = 2-digit year)
# National: oesm{YY}nat.zip  -> all_data_M_{YYYY}.xlsx
# State:    oesm{YY}st.zip   -> oesm{YY}st/all_data_M_{YYYY}.xlsx
# Metro:    oesm{YY}ma.zip   -> oesm{YY}ma/all_data_M_{YYYY}.xlsx

# Column mappings from BLS XLSX to our schema
# BLS uses: OCC_CODE, OCC_TITLE, OCC_GROUP, I_GROUP, TOT_EMP, A_MEAN,
#           AREA_TITLE, AREA_TYPE, PRIM_STATE


def _bls_urls(year: int) -> dict[str, str]:
    """Generate BLS OES download URLs for a given year."""
    yy = str(year)[-2:]
    base = config.BLS_BASE_URL
    return {
        "national": f"{base}/oesm{yy}nat.zip",
        "state": f"{base}/oesm{yy}st.zip",
        "metro": f"{base}/oesm{yy}ma.zip",
    }


def _download_zip(url: str, dest_dir: Path) -> Path:
    """Download a ZIP file and return the local path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    dest_path = dest_dir / filename

    if dest_path.exists():
        print(f"  Using cached: {dest_path.name}")
        return dest_path

    print(f"  Downloading: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (research project, BLS data download)",
    }
    resp = requests.get(url, timeout=120, headers=headers)
    resp.raise_for_status()
    dest_path.write_bytes(resp.content)
    print(f"  Saved: {dest_path.name} ({len(resp.content):,} bytes)")
    return dest_path


def _find_xlsx_in_zip(zip_path: Path, prefer: str | None = None) -> str:
    """Find the main data XLSX file inside a BLS ZIP.

    If prefer is set (e.g. "MSA"), look for files containing that string first.
    """
    with zipfile.ZipFile(zip_path) as zf:
        xlsx_files = [n for n in zf.namelist() if n.endswith(".xlsx")]

        # Try preferred pattern first
        if prefer:
            preferred = [n for n in xlsx_files if prefer.upper() in n.upper()]
            if preferred:
                return preferred[0]

        # Try "all_data" pattern (older format)
        all_data = [n for n in xlsx_files if "all_data" in n.lower()]
        if all_data:
            return all_data[0]

        # Fallback: any xlsx (skip file_descriptions)
        data_files = [n for n in xlsx_files
                      if "file_description" not in n.lower()]
        if data_files:
            return data_files[0]
        if xlsx_files:
            return xlsx_files[0]
    raise FileNotFoundError(f"No XLSX found in {zip_path}")


def _read_xlsx_from_zip(zip_path: Path,
                        prefer: str | None = None) -> list[dict]:
    """Extract and read the XLSX from a BLS ZIP file.

    Returns list of dicts with original BLS column names.
    """
    import openpyxl

    xlsx_name = _find_xlsx_in_zip(zip_path, prefer=prefer)
    print(f"  Reading: {xlsx_name}")
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(xlsx_name) as xlsx_file:
            wb = openpyxl.load_workbook(io.BytesIO(xlsx_file.read()),
                                        read_only=True, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            headers = [str(h).strip() if h else "" for h in next(rows_iter)]
            data = []
            for row in rows_iter:
                data.append(dict(zip(headers, row)))
            wb.close()
    return data


def _clean_numeric(val) -> int | None:
    """Convert a BLS cell value to int, returning None for suppressed data."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ("**", "*", "#", "", "N/A", "na"):
        return None
    # Remove commas
    s = s.replace(",", "")
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _filter_and_map_national(rows: list[dict], year: int) -> list[dict]:
    """Filter national data and map to our schema."""
    results = []
    for row in rows:
        # Keep cross-industry occupations at all levels
        i_group = str(row.get("I_GROUP", "")).strip()
        occ_group = str(row.get("O_GROUP", "")).strip()
        if i_group != "cross-industry":
            continue
        if occ_group not in ("major", "minor", "broad", "detailed"):
            continue

        emp = _clean_numeric(row.get("TOT_EMP"))
        wage = _clean_numeric(row.get("A_MEAN"))
        if emp is None or wage is None or emp <= 0 or wage <= 0:
            continue

        occ_code = str(row.get("OCC_CODE", "")).strip()
        occ_title = str(row.get("OCC_TITLE", "")).strip()
        prefix = occ_code[:2] if "-" in occ_code else ""
        major_group = config.SOC_MAJOR_GROUPS.get(prefix, occ_title)

        results.append({
            "year": year,
            "region_type": "National",
            "region": config.COUNTRIES["USA"]["national_region_name"],
            "occupation_code": occ_code,
            "occupation_title": occ_title,
            "major_group_name": major_group,
            "employment": emp,
            "mean_annual_wage": wage,
        })
    return results


def _filter_and_map_state(rows: list[dict], year: int) -> list[dict]:
    """Filter state data and map to our schema."""
    results = []
    for row in rows:
        i_group = str(row.get("I_GROUP", "")).strip()
        occ_group = str(row.get("O_GROUP", "")).strip()
        if i_group != "cross-industry":
            continue
        if occ_group not in ("major", "minor", "broad", "detailed"):
            continue

        emp = _clean_numeric(row.get("TOT_EMP"))
        wage = _clean_numeric(row.get("A_MEAN"))
        if emp is None or wage is None or emp <= 0 or wage <= 0:
            continue

        # State name from AREA_TITLE (e.g., "California")
        area_title = str(row.get("AREA_TITLE", "")).strip()
        if not area_title:
            continue

        occ_code = str(row.get("OCC_CODE", "")).strip()
        occ_title = str(row.get("OCC_TITLE", "")).strip()
        prefix = occ_code[:2] if "-" in occ_code else ""
        major_group = config.SOC_MAJOR_GROUPS.get(prefix, occ_title)

        results.append({
            "year": year,
            "region_type": "State",
            "region": area_title,
            "occupation_code": occ_code,
            "occupation_title": occ_title,
            "major_group_name": major_group,
            "employment": emp,
            "mean_annual_wage": wage,
        })
    return results


def _filter_and_map_metro(rows: list[dict], year: int) -> list[dict]:
    """Filter metro data and map to our schema."""
    results = []
    for row in rows:
        i_group = str(row.get("I_GROUP", "")).strip()
        occ_group = str(row.get("O_GROUP", "")).strip()
        if i_group != "cross-industry":
            continue
        if occ_group not in ("major", "minor", "broad", "detailed"):
            continue

        # Only MSAs (AREA_TYPE == 4 for MSA in newer files, or 3)
        area_type = str(row.get("AREA_TYPE", "")).strip()
        if area_type not in ("3", "4"):
            continue

        emp = _clean_numeric(row.get("TOT_EMP"))
        wage = _clean_numeric(row.get("A_MEAN"))
        if emp is None or wage is None or emp <= 0 or wage <= 0:
            continue

        area_title = str(row.get("AREA_TITLE", "")).strip()
        if not area_title:
            continue

        occ_code = str(row.get("OCC_CODE", "")).strip()
        occ_title = str(row.get("OCC_TITLE", "")).strip()
        prefix = occ_code[:2] if "-" in occ_code else ""
        major_group = config.SOC_MAJOR_GROUPS.get(prefix, occ_title)

        results.append({
            "year": year,
            "region_type": "Metro",
            "region": area_title,
            "occupation_code": occ_code,
            "occupation_title": occ_title,
            "major_group_name": major_group,
            "employment": emp,
            "mean_annual_wage": wage,
        })
    return results


def fetch_and_parse(year: int, raw_dir: Path | None = None) -> Path:
    """Download BLS OES data for a year and produce a combined CSV.

    Returns the path to the combined CSV file.
    """
    if raw_dir is None:
        raw_dir = config.RAW_DIR

    urls = _bls_urls(year)
    all_records: list[dict] = []

    # National
    print("Fetching BLS national data...")
    nat_zip = _download_zip(urls["national"], raw_dir)
    nat_rows = _read_xlsx_from_zip(nat_zip)
    nat_records = _filter_and_map_national(nat_rows, year)
    print(f"  National: {len(nat_records)} occupations")
    all_records.extend(nat_records)

    # State
    print("Fetching BLS state data...")
    st_zip = _download_zip(urls["state"], raw_dir)
    st_rows = _read_xlsx_from_zip(st_zip)
    st_records = _filter_and_map_state(st_rows, year)
    print(f"  States: {len(st_records)} records")
    all_records.extend(st_records)

    # Metro (prefer MSA file over BOS nonmetropolitan file)
    print("Fetching BLS metro data...")
    ma_zip = _download_zip(urls["metro"], raw_dir)
    ma_rows = _read_xlsx_from_zip(ma_zip, prefer="MSA")
    ma_records = _filter_and_map_metro(ma_rows, year)
    print(f"  Metros: {len(ma_records)} records")
    all_records.extend(ma_records)

    # Write combined CSV
    csv_path = raw_dir / f"bls_oes_{year}_combined.csv"
    fieldnames = [
        "year", "region_type", "region", "occupation_code",
        "occupation_title", "major_group_name", "employment",
        "mean_annual_wage",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nCombined CSV: {csv_path.name} ({len(all_records):,} records)")
    return csv_path
