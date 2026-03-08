"""Export time-series JSON files for the frontend stacked area chart.

Supports two data sources:
  1. BLS OES (US): Level 1 (22 major groups) employment + GDP, 2003-2024
  2. ILOSTAT Modelled Estimates (US + India): 8 ISCO-08 groups, 1991-2025

Usage:
    python -m scripts.pipeline.export_timeseries --country us --source oes
    python -m scripts.pipeline.export_timeseries --source ilostat
"""

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.pipeline import config
from scripts.pipeline.fetch_bls import (
    _bls_urls, _download_zip, _find_xlsx_in_zip, _clean_numeric,
)

# ─── Constants ────────────────────────────────────────────────────────

# ILOSTAT API base
ILOSTAT_API = "https://rplumber.ilo.org/data/indicator"

# ILOSTAT indicator codes
ILOSTAT_EMP_INDICATOR = "EMP_2EMP_SEX_OCU_NB"        # Employment by occupation
ILOSTAT_EARN_INDICATOR = "EAR_EMTA_SEX_OCU_CUR_NB"  # Mean monthly earnings

# ILOSTAT country codes
ILOSTAT_COUNTRIES = {
    "us": "USA",
    "in": "IND",
}

# ISCO-08 1-digit major groups (merge 6=Agriculture and 9=Elementary into "96")
ISCO08_GROUPS = [
    {"id": "1", "name": "Managers"},
    {"id": "2", "name": "Professionals"},
    {"id": "3", "name": "Technicians and Associate Professionals"},
    {"id": "4", "name": "Clerical Support Workers"},
    {"id": "5", "name": "Service and Sales Workers"},
    {"id": "7", "name": "Craft and Related Trades Workers"},
    {"id": "8", "name": "Plant and Machine Operators and Assemblers"},
    {"id": "96", "name": "Agriculture and Elementary Occupations"},
]

ISCO08_COLORS = {
    "1": "#A973BE",
    "2": "#F1866C",
    "3": "#488098",
    "4": "#6A6AAD",
    "5": "#77C898",
    "7": "#DAA520",
    "8": "#CD853F",
    "96": "#556B2F",
}

# BLS OES year range
OES_YEAR_START = 2003
OES_YEAR_END = 2024

# SOC Major Groups (Level 1)
SOC_MAJOR_GROUP_IDS = [
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "31", "33", "35", "37", "39", "41", "43", "45", "47", "49",
    "51", "53",
]


def _make_region_id(region_type: str, region_name: str) -> str:
    """Create a URL-safe region ID from type and name."""
    slug = re.sub(r"[^a-z0-9]+", "-", region_name.lower()).strip("-")
    return f"{region_type.lower()}-{slug}"


# ─── BLS OES Extraction ──────────────────────────────────────────────

def _find_data_file_in_zip(zip_path: Path, prefer: str | None = None) -> str:
    """Find the main data file (XLS or XLSX) inside a BLS ZIP."""
    with zipfile.ZipFile(zip_path) as zf:
        all_files = zf.namelist()
        data_files = [
            n for n in all_files
            if (n.endswith(".xlsx") or n.endswith(".xls"))
            and "file_description" not in n.lower()
            and "field_description" not in n.lower()
            and "/~$" not in n and not n.startswith("~$")
        ]

        if prefer:
            preferred = [n for n in data_files if prefer.upper() in n.upper()]
            if preferred:
                return preferred[0]

        # Try "all_data" or "national" or "state" patterns
        for pattern in ["all_data", "national", "state", "MSA"]:
            matches = [n for n in data_files if pattern.lower() in n.lower()]
            if matches:
                return matches[0]

        if data_files:
            return data_files[0]
    raise FileNotFoundError(f"No data file found in {zip_path}")


def _normalize_oes_columns(row: dict) -> dict:
    """Normalize BLS column names across years.

    Pre-2010: lowercase (occ_code, group, tot_emp, a_mean)
    2010-2013: uppercase (OCC_CODE, GROUP, TOT_EMP, A_MEAN)
    2014+: uppercase with OCC_GROUP (OCC_CODE, OCC_GROUP, TOT_EMP, A_MEAN)
    2020+: O_GROUP + I_GROUP added
    """
    normalized = {}
    for key, val in row.items():
        upper_key = key.upper().strip()
        # Map 'GROUP' -> 'OCC_GROUP' for consistency
        if upper_key == "GROUP":
            upper_key = "OCC_GROUP"
        normalized[upper_key] = val
    return normalized


def _read_data_from_zip(zip_path: Path,
                        prefer: str | None = None) -> list[dict]:
    """Read the main data file from a BLS ZIP, handling both XLS and XLSX.

    Returns rows with normalized uppercase column names.
    """
    data_name = _find_data_file_in_zip(zip_path, prefer=prefer)

    with zipfile.ZipFile(zip_path) as zf:
        file_bytes = zf.read(data_name)

    if data_name.endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(
            io.BytesIO(file_bytes), read_only=True, data_only=True,
        )
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h).strip() if h else "" for h in next(rows_iter)]
        data = [dict(zip(headers, row_vals)) for row_vals in rows_iter]
        wb.close()
    else:
        # XLS format (pre-2014)
        import xlrd
        wb = xlrd.open_workbook(file_contents=file_bytes)
        ws = wb.sheet_by_index(0)
        headers = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]
        data = []
        for r in range(1, ws.nrows):
            row = {headers[c]: ws.cell_value(r, c) for c in range(ws.ncols)}
            data.append(row)

    # Normalize column names
    return [_normalize_oes_columns(row) for row in data]


def _extract_oes_year(year: int, raw_dir: Path) -> dict:
    """Download and extract Level 1 data for a single OES year.

    Returns dict: { regionId: { majorGroupId: { emp, gdp } } }
    """
    urls = _bls_urls(year)
    year_data = {}

    for geo_type, url in urls.items():
        try:
            zip_path = _download_zip(url, raw_dir / "timeseries")
        except Exception as e:
            print(f"    WARNING: Failed to download {geo_type} for {year}: {e}")
            continue

        prefer = "MSA" if geo_type == "metro" else None
        try:
            rows = _read_data_from_zip(zip_path, prefer=prefer)
            for row in rows:
                _process_oes_row(row, year, geo_type, year_data)
        except Exception as e:
            print(f"    WARNING: Failed to parse {geo_type} for {year}: {e}")
            continue

    return year_data


def _process_oes_row(row: dict, year: int, geo_type: str,
                     year_data: dict) -> None:
    """Process a single OES XLSX row, extracting Level 1 (major group) data.

    Handles format differences across BLS OES years:
    - Pre-2020: OCC_GROUP (not O_GROUP), no I_GROUP column, national has no AREA_TYPE
    - 2020+: O_GROUP, I_GROUP=cross-industry, AREA_TYPE
    """
    # Determine occupation group - column names are now normalized to uppercase
    o_group = str(row.get("O_GROUP", row.get("OCC_GROUP", ""))).strip()
    if o_group != "major":
        return

    # Filter cross-industry if I_GROUP exists (newer format)
    i_group = str(row.get("I_GROUP", "")).strip()
    if i_group and i_group != "cross-industry":
        return

    occ_code = str(row.get("OCC_CODE", "")).strip()
    if not occ_code or not occ_code.endswith("-0000"):
        return
    # Skip the total (00-0000)
    if occ_code == "00-0000":
        return

    emp = _clean_numeric(row.get("TOT_EMP"))
    wage = _clean_numeric(row.get("A_MEAN"))
    if emp is None or emp <= 0:
        return

    major_id = occ_code[:2]
    gdp = (emp * wage) if wage and wage > 0 else None

    # Determine region — handle column name differences across years
    if geo_type == "national":
        region_name = "United States"
        region_type = "National"
    elif geo_type == "state":
        # 2003-2009: STATE column; 2010+: AREA_TITLE; some years: AREA_NAME
        region_name = str(
            row.get("AREA_TITLE", row.get("AREA_NAME",
                row.get("STATE", "")))
        ).strip()
        region_type = "State"
    else:
        area_type = str(row.get("AREA_TYPE", "")).strip()
        if area_type and area_type not in ("3", "4"):
            return
        region_name = str(
            row.get("AREA_TITLE", row.get("AREA_NAME", ""))
        ).strip()
        region_type = "Metro"

    if not region_name:
        return

    region_id = _make_region_id(region_type, region_name)
    if region_id not in year_data:
        year_data[region_id] = {
            "name": region_name,
            "regionType": region_type,
        }
    if major_id not in year_data[region_id]:
        year_data[region_id][major_id] = {"emp": emp}
        if gdp is not None:
            year_data[region_id][major_id]["gdp"] = gdp
    else:
        # Should not happen for Level 1, but be safe
        year_data[region_id][major_id]["emp"] += emp
        if gdp is not None:
            year_data[region_id][major_id]["gdp"] = \
                year_data[region_id][major_id].get("gdp", 0) + gdp


def export_oes(raw_dir: Path | None = None,
               start_year: int = OES_YEAR_START,
               end_year: int = OES_YEAR_END) -> None:
    """Export BLS OES time-series JSON files."""
    if raw_dir is None:
        raw_dir = config.RAW_DIR

    years = list(range(start_year, end_year + 1))
    print(f"\n=== BLS OES Time Series ({start_year}-{end_year}) ===\n")

    # Collect data across all years
    # all_data[regionId][majorGroupId] = { emp: [val_per_year], gdp: [...] }
    all_data: dict = {}
    region_info: dict = {}  # regionId -> { name, regionType }

    for year in years:
        print(f"  Processing {year}...")
        year_data = _extract_oes_year(year, raw_dir)
        year_idx = year - start_year

        for region_id, region_data in year_data.items():
            name = region_data.get("name", region_id)
            rtype = region_data.get("regionType", "National")

            if region_id not in region_info:
                region_info[region_id] = {"name": name, "regionType": rtype}
            if region_id not in all_data:
                all_data[region_id] = {}

            for group_id in SOC_MAJOR_GROUP_IDS:
                if group_id not in all_data[region_id]:
                    all_data[region_id][group_id] = {
                        "emp": [None] * len(years),
                        "gdp": [None] * len(years),
                    }
                if group_id in region_data and isinstance(region_data[group_id], dict):
                    gd = region_data[group_id]
                    all_data[region_id][group_id]["emp"][year_idx] = gd.get("emp")
                    all_data[region_id][group_id]["gdp"][year_idx] = gd.get("gdp")

    # Build output JSON — split into base (national+state) and metro
    groups = []
    for gid in SOC_MAJOR_GROUP_IDS:
        groups.append({
            "id": gid,
            "name": config.SOC_MAJOR_GROUPS.get(gid, f"Group {gid}"),
            "color": config.SOC_MAJOR_GROUP_COLORS.get(gid, "#999999"),
        })

    base_regions = []
    metro_regions = []
    base_data = {}
    metro_data = {}

    for region_id, info in sorted(region_info.items()):
        entry = {
            "regionId": region_id,
            "name": info["name"],
            "regionType": info["regionType"],
        }
        region_ts = {}
        for group_id in SOC_MAJOR_GROUP_IDS:
            if region_id in all_data and group_id in all_data[region_id]:
                gd = all_data[region_id][group_id]
                ts_entry = {"emp": gd["emp"]}
                if any(v is not None for v in gd["gdp"]):
                    ts_entry["gdp"] = gd["gdp"]
                region_ts[group_id] = ts_entry
        if not region_ts:
            continue

        if info["regionType"] == "Metro":
            metro_regions.append(entry)
            metro_data[region_id] = region_ts
        else:
            base_regions.append(entry)
            base_data[region_id] = region_ts

    metadata = {
        "source": "BLS OES",
        "country": "us",
        "years": years,
        "hasGdp": True,
    }

    # Write base (national + state)
    base_json = {
        "metadata": metadata,
        "groups": groups,
        "regions": base_regions,
        "data": base_data,
    }
    base_path = config.PUBLIC_DATA_DIR / "timeseries-us-oes.json"
    with open(base_path, "w", encoding="utf-8") as f:
        json.dump(base_json, f, separators=(",", ":"))
    print(f"\n  Base: {base_path.name} ({len(base_regions)} regions, "
          f"{len(base_data)} with data)")

    # Write metro
    if metro_regions:
        metro_json = {
            "metadata": metadata,
            "groups": groups,
            "regions": metro_regions,
            "data": metro_data,
        }
        metro_path = config.PUBLIC_DATA_DIR / "timeseries-us-oes-metro.json"
        with open(metro_path, "w", encoding="utf-8") as f:
            json.dump(metro_json, f, separators=(",", ":"))
        print(f"  Metro: {metro_path.name} ({len(metro_regions)} regions)")

    print(f"\n  Done: {len(years)} years, {len(groups)} groups")


# ─── ILOSTAT Extraction ──────────────────────────────────────────────

def _fetch_ilostat_csv(indicator: str, country_iso3: str) -> list[dict]:
    """Fetch ILOSTAT indicator data as CSV rows."""
    url = f"{ILOSTAT_API}/?id={indicator}&ref_area={country_iso3}&sex=SEX_T"
    print(f"  Fetching: {url[:80]}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (research project)",
        "Accept": "text/csv",
    }
    resp = requests.get(url, timeout=60, headers=headers)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def _parse_ilostat_employment(rows: list[dict], merge_6_9: bool = True
                              ) -> dict:
    """Parse ILOSTAT employment CSV into { year: { groupId: value } }.

    If merge_6_9=True, merges ISCO-08 groups 6 and 9 into combined "96".
    If merge_6_9=False, keeps groups 6 and 9 separate.
    """
    data = {}
    for row in rows:
        year = int(row.get("time", row.get("TIME_PERIOD", "0")))
        if year < 1990:
            continue

        classif = row.get("classif1", row.get("CLASSIF1", ""))
        # Extract ISCO-08 1-digit code (e.g., "OCU_ISCO08_1" -> "1")
        if "OCU_ISCO08_" not in classif:
            continue
        group_code = classif.replace("OCU_ISCO08_", "").strip()
        if not group_code or group_code == "TOTAL":
            continue

        value_str = row.get("obs_value", row.get("OBS_VALUE", ""))
        try:
            value = float(value_str) * 1000  # ILOSTAT reports in thousands
        except (ValueError, TypeError):
            continue

        # Merge groups 6 and 9 into "96"
        if merge_6_9 and group_code in ("6", "9"):
            group_code = "96"

        if year not in data:
            data[year] = {}
        if group_code in data[year]:
            data[year][group_code] += value
        else:
            data[year][group_code] = value

    return data


def _parse_ilostat_earnings(rows: list[dict], currency: str = "USD") -> dict:
    """Parse ILOSTAT earnings CSV into { year: { groupId: monthly_value } }.

    Returns earnings per ISCO-08 1-digit group (NOT merged).
    Groups 6 and 9 kept separate so GDP can be computed correctly
    before merging into "96".
    """
    data = {}
    for row in rows:
        year = int(row.get("time", row.get("TIME_PERIOD", "0")))
        if year < 1990:
            continue

        classif = row.get("classif1", row.get("CLASSIF1", ""))
        # Accept both ISCO-08 and ISCO-88 (identical at 1-digit level)
        group_code = None
        if "OCU_ISCO08_" in classif:
            group_code = classif.replace("OCU_ISCO08_", "").strip()
        elif "OCU_ISCO88_" in classif:
            group_code = classif.replace("OCU_ISCO88_", "").strip()
        if not group_code or group_code in ("TOTAL", "X"):
            continue

        # Filter by currency (LCU, PPP, or USD)
        # classif2 values: CUR_TYPE_USD, CUR_TYPE_LCU, CUR_TYPE_PPP
        cur = row.get("classif2", row.get("CLASSIF2", ""))
        if currency == "USD" and "USD" not in cur:
            continue
        elif currency == "LCU" and "LCU" not in cur:
            continue
        elif currency == "PPP" and "PPP" not in cur:
            continue

        value_str = row.get("obs_value", row.get("OBS_VALUE", ""))
        try:
            value = float(value_str)
        except (ValueError, TypeError):
            continue

        if year not in data:
            data[year] = {}
        data[year][group_code] = value

    return data


def export_ilostat(country: str = "both") -> None:
    """Export ILOSTAT time-series JSON files."""
    print(f"\n=== ILOSTAT Time Series ===\n")

    countries_to_process = []
    if country in ("both", "us"):
        countries_to_process.append("us")
    if country in ("both", "in"):
        countries_to_process.append("in")

    for cc in countries_to_process:
        iso3 = ILOSTAT_COUNTRIES[cc]
        print(f"\n  Country: {cc} ({iso3})")

        # Fetch employment data (merged 6+9 for display, raw for GDP calc)
        emp_rows = _fetch_ilostat_csv(ILOSTAT_EMP_INDICATOR, iso3)
        emp_data = _parse_ilostat_employment(emp_rows, merge_6_9=True)
        emp_raw = _parse_ilostat_employment(emp_rows, merge_6_9=False)

        if not emp_data:
            print(f"    WARNING: No employment data found for {cc}")
            continue

        years = sorted(emp_data.keys())
        print(f"    Employment: {years[0]}-{years[-1]} ({len(years)} years)")

        # Fetch earnings data (USD for cross-country comparability)
        earn_rows = _fetch_ilostat_csv(ILOSTAT_EARN_INDICATOR, iso3)
        earn_data = _parse_ilostat_earnings(earn_rows, currency="USD")
        earn_years = sorted(earn_data.keys()) if earn_data else []
        if earn_years:
            print(f"    Earnings: {earn_years[0]}-{earn_years[-1]} "
                  f"({len(earn_years)} years, USD)")
        else:
            print(f"    Earnings: none available")

        # Determine the national region ID
        country_name = "United States" if cc == "us" else "India"
        region_id = _make_region_id("National", country_name)

        # Build time series arrays indexed by year position
        ts_data = {}
        valid_groups = set()
        has_any_gdp = False
        for group in ISCO08_GROUPS:
            gid = group["id"]
            emp_series = []
            gdp_series = []
            for year in years:
                val = emp_data.get(year, {}).get(gid)
                emp_series.append(round(val) if val is not None else None)
                if val is not None:
                    valid_groups.add(gid)

                # Compute GDP = emp × monthly_earnings × 12
                # For merged "96": GDP = emp_6 × earn_6 × 12 + emp_9 × earn_9 × 12
                year_earnings = earn_data.get(year, {})
                if gid == "96":
                    # Use raw (unmerged) employment for accurate GDP
                    raw_year = emp_raw.get(year, {})
                    e6 = raw_year.get("6", 0)
                    e9 = raw_year.get("9", 0)
                    earn_6 = year_earnings.get("6")
                    earn_9 = year_earnings.get("9")
                    gdp_96 = 0
                    has_earn = False
                    if e6 > 0 and earn_6 is not None:
                        gdp_96 += e6 * earn_6 * 12
                        has_earn = True
                    if e9 > 0 and earn_9 is not None:
                        gdp_96 += e9 * earn_9 * 12
                        has_earn = True
                    if has_earn:
                        gdp_series.append(round(gdp_96))
                        has_any_gdp = True
                    else:
                        gdp_series.append(None)
                else:
                    earn_val = year_earnings.get(gid)
                    if val is not None and earn_val is not None:
                        gdp_val = round(val * earn_val * 12)
                        gdp_series.append(gdp_val)
                        has_any_gdp = True
                    else:
                        gdp_series.append(None)

            ts_entry = {"emp": emp_series}
            if any(v is not None for v in gdp_series):
                ts_entry["gdp"] = gdp_series
            ts_data[gid] = ts_entry

        # Filter to groups that have data
        groups = [
            {
                "id": g["id"],
                "name": g["name"],
                "color": ISCO08_COLORS.get(g["id"], "#999999"),
            }
            for g in ISCO08_GROUPS
            if g["id"] in valid_groups
        ]

        output = {
            "metadata": {
                "source": "ILOSTAT Modelled Estimates",
                "country": cc,
                "years": years,
                "hasGdp": has_any_gdp,
            },
            "groups": groups,
            "regions": [{
                "regionId": region_id,
                "name": country_name,
                "regionType": "National",
            }],
            "data": {
                region_id: {
                    gid: ts_data[gid]
                    for gid in ts_data
                    if gid in valid_groups
                },
            },
        }

        out_path = config.PUBLIC_DATA_DIR / f"timeseries-ilostat-{cc}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, separators=(",", ":"))
        print(f"    Output: {out_path.name} ({len(groups)} groups, "
              f"{len(years)} years)")

    print(f"\n  Done.")


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Export time-series JSON for the frontend"
    )
    parser.add_argument(
        "--source", choices=["oes", "ilostat", "all"], default="all",
        help="Data source to export (default: all)",
    )
    parser.add_argument(
        "--country", default="us",
        help="Country code for OES (default: us); ILOSTAT always does both",
    )
    parser.add_argument(
        "--start-year", type=int, default=OES_YEAR_START,
        help=f"OES start year (default: {OES_YEAR_START})",
    )
    parser.add_argument(
        "--end-year", type=int, default=OES_YEAR_END,
        help=f"OES end year (default: {OES_YEAR_END})",
    )
    args = parser.parse_args()

    if args.source in ("oes", "all"):
        export_oes(start_year=args.start_year, end_year=args.end_year)

    if args.source in ("ilostat", "all"):
        export_ilostat()


if __name__ == "__main__":
    main()
