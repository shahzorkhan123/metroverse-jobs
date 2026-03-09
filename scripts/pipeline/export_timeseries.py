"""Export time-series JSON files for the frontend stacked area chart.

Supports three data sources:
  1. BLS OES (US): Level 1 (22 major groups) employment + GDP, 2003-2024
  2. ILOSTAT Modelled Estimates (US + India): 8 ISCO-08 groups, 1991-2025
  3. PLFS Annual Reports (India): 9 NCO divisions, 2018-2024

Usage:
    python -m scripts.pipeline.export_timeseries --country us --source oes
    python -m scripts.pipeline.export_timeseries --source ilostat
    python -m scripts.pipeline.export_timeseries --source plfs
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


# ─── PLFS India Extraction ───────────────────────────────────────────

# NCO 2015 Division groups (India — same as ISCO-08 at 1-digit)
NCO_DIVISIONS = [
    {"id": "1", "name": "Managers"},
    {"id": "2", "name": "Professionals"},
    {"id": "3", "name": "Technicians and Associate Professionals"},
    {"id": "4", "name": "Clerical Support Workers"},
    {"id": "5", "name": "Service and Sales Workers"},
    {"id": "6", "name": "Skilled Agricultural, Forestry and Fishery Workers"},
    {"id": "7", "name": "Craft and Related Trades Workers"},
    {"id": "8", "name": "Plant and Machine Operators and Assemblers"},
    {"id": "9", "name": "Elementary Occupations"},
]

NCO_COLORS = {
    "1": "#A973BE", "2": "#F1866C", "3": "#488098", "4": "#6A6AAD",
    "5": "#77C898", "6": "#556B2F", "7": "#DAA520", "8": "#CD853F",
    "9": "#708090",
}

# PLFS % distribution of workers by NCO division (MoSPI API, national level)
# Keys are calendar years (fiscal year end: 2017-18 → 2018)
PLFS_PERCENTAGES = {
    2018: {"1": 7.4, "2": 4.1, "3": 4.0, "4": 2.0, "5": 9.2, "6": 31.2, "7": 11.8, "8": 5.8, "9": 24.7},
    2019: {"1": 8.2, "2": 4.2, "3": 4.1, "4": 2.1, "5": 9.6, "6": 30.9, "7": 11.8, "8": 5.5, "9": 23.6},
    2020: {"1": 8.7, "2": 4.2, "3": 3.8, "4": 1.9, "5": 8.7, "6": 33.2, "7": 11.3, "8": 5.5, "9": 22.8},
    2021: {"1": 8.4, "2": 3.8, "3": 3.5, "4": 1.8, "5": 8.1, "6": 35.1, "7": 11.6, "8": 5.3, "9": 22.5},
    2022: {"1": 7.2, "2": 5.0, "3": 2.2, "4": 2.0, "5": 9.8, "6": 35.4, "7": 9.7, "8": 5.4, "9": 23.3},
    2023: {"1": 3.7, "2": 5.2, "3": 2.1, "4": 1.9, "5": 11.4, "6": 36.9, "7": 10.8, "8": 5.2, "9": 22.8},
    2024: {"1": 3.2, "2": 5.3, "3": 2.3, "4": 2.1, "5": 11.5, "6": 38.0, "7": 11.1, "8": 5.3, "9": 21.3},
}

# PLFS average monthly wage/salary earnings (Rs.) by NCO division
# From Table 50 / Table 33 / Table 55 in each year's annual report
# "rural+urban, person" row — regular wage/salaried employees only
# 2017-18 and 2018-19 reports did not publish wage-by-occupation tables
PLFS_WAGES: dict[int, dict[str, float] | None] = {
    2018: None,  # Not published in 2017-18 report
    2019: None,  # Not published in 2018-19 report
    2020: {"1": 26426, "2": 20352, "3": 21629, "4": 17210, "5": 11182, "6": 12836, "7": 11971, "8": 11307, "9": 9427},
    2021: {"1": 29024, "2": 27305, "3": 23597, "4": 19173, "5": 12404, "6": 11316, "7": 11745, "8": 12339, "9": 10160},
    2022: {"1": 38023, "2": 31158, "3": 23845, "4": 20538, "5": 13220, "6": 13538, "7": 13512, "8": 14127, "9": 9702},
    2023: {"1": 44903, "2": 32530, "3": 22578, "4": 21373, "5": 13530, "6": 13526, "7": 13901, "8": 15139, "9": 10420},
    2024: {"1": 42993, "2": 35776, "3": 24199, "4": 23616, "5": 14628, "6": 11319, "7": 15350, "8": 15906, "9": 10667},
}

# Census 2011 state populations (millions) — used as proportional weights
# Telangana carved from AP in 2014; PLFS (2017+) treats them separately
CENSUS_2011_POP = {
    "Andaman and Nicobar Islands": 0.38,
    "Andhra Pradesh": 49.39, "Arunachal Pradesh": 1.38, "Assam": 31.21,
    "Bihar": 104.10, "Chandigarh": 1.06, "Chhattisgarh": 25.54,
    "Dadra and Nagar Haveli and Daman and Diu": 0.59,
    "Delhi": 16.79, "Goa": 1.46,
    "Gujarat": 60.44, "Haryana": 25.35, "Himachal Pradesh": 6.86,
    "Jammu and Kashmir": 12.55, "Jharkhand": 32.99, "Karnataka": 61.10,
    "Kerala": 33.39, "Ladakh": 0.27, "Lakshadweep": 0.06,
    "Madhya Pradesh": 72.63, "Maharashtra": 112.37,
    "Manipur": 2.86, "Meghalaya": 2.97, "Mizoram": 1.09, "Nagaland": 1.98,
    "Odisha": 41.97, "Puducherry": 1.25, "Punjab": 27.74,
    "Rajasthan": 68.55, "Sikkim": 0.61,
    "Tamil Nadu": 72.15, "Telangana": 35.19, "Tripura": 3.67,
    "Uttarakhand": 10.09, "Uttar Pradesh": 199.81, "West Bengal": 91.28,
}

# WPR (Worker Population Ratio, %) by state × year from MoSPI PLFS API
# Keys: state name → { calendar_year: WPR }; rural+urban, person, PS+SS, all ages
STATE_WPR = {
    "Andaman and Nicobar Islands": {2018: 37.4, 2019: 38.3, 2020: 40.6, 2021: 48.3, 2022: 46.4, 2023: 48.8, 2024: 47.0},
    "Andhra Pradesh":    {2018: 45.0, 2019: 43.0, 2020: 44.2, 2021: 46.5, 2022: 46.2, 2023: 46.6, 2024: 45.6},
    "Arunachal Pradesh": {2018: 30.7, 2019: 31.6, 2020: 32.9, 2021: 35.3, 2022: 34.4, 2023: 47.4, 2024: 51.1},
    "Assam":             {2018: 32.9, 2019: 32.5, 2020: 31.9, 2021: 38.1, 2022: 37.8, 2023: 30.2, 2024: 47.2},
    "Bihar":             {2018: 23.6, 2019: 24.1, 2020: 26.0, 2021: 26.6, 2022: 25.6, 2023: 30.2, 2024: 33.5},
    "Chandigarh":        {2018: 35.6, 2019: 37.4, 2020: 34.2, 2021: 34.5, 2022: 33.3, 2023: 36.7, 2024: 40.4},
    "Chhattisgarh":      {2018: 45.7, 2019: 44.7, 2020: 48.7, 2021: 48.4, 2022: 48.5, 2023: 52.6, 2024: 54.2},
    "Dadra and Nagar Haveli and Daman and Diu": {2018: 47.9, 2019: 46.4, 2020: 53.0, 2021: 43.0, 2022: 51.6, 2023: 47.5, 2024: 51.1},
    "Delhi":             {2018: 32.8, 2019: 33.6, 2020: 34.0, 2021: 33.7, 2022: 33.0, 2023: 35.0, 2024: 35.2},
    "Goa":               {2018: 34.7, 2019: 36.6, 2020: 37.6, 2021: 35.5, 2022: 33.8, 2023: 37.0, 2024: 36.5},
    "Gujarat":           {2018: 36.2, 2019: 38.3, 2020: 42.4, 2021: 43.3, 2022: 44.3, 2023: 47.2, 2024: 49.1},
    "Haryana":           {2018: 30.5, 2019: 31.1, 2020: 32.1, 2021: 33.1, 2022: 32.3, 2023: 34.1, 2024: 36.1},
    "Himachal Pradesh":  {2018: 46.4, 2019: 50.1, 2020: 55.6, 2021: 55.4, 2022: 55.8, 2023: 58.6, 2024: 57.2},
    "Jammu and Kashmir": {2018: 38.6, 2019: 40.7, 2020: 39.2, 2021: 42.0, 2022: 44.0, 2023: 45.1, 2024: 44.9},
    "Jharkhand":         {2018: 28.8, 2019: 30.7, 2020: 37.6, 2021: 42.2, 2022: 43.2, 2023: 41.9, 2024: 43.9},
    "Karnataka":         {2018: 38.1, 2019: 38.4, 2020: 41.7, 2021: 43.5, 2022: 41.7, 2023: 43.9, 2024: 44.1},
    "Kerala":            {2018: 32.4, 2019: 35.9, 2020: 36.5, 2021: 37.6, 2022: 39.7, 2023: 41.2, 2024: 42.1},
    "Ladakh":            {2020: 45.6, 2021: 53.8, 2022: 43.4, 2023: 43.8, 2024: 47.9},
    "Lakshadweep":       {2018: 26.0, 2019: 23.9, 2020: 38.0, 2021: 29.7, 2022: 29.1, 2023: 27.1, 2024: 33.8},
    "Madhya Pradesh":    {2018: 40.0, 2019: 38.4, 2020: 42.8, 2021: 44.9, 2022: 45.1, 2023: 47.6, 2024: 50.6},
    "Maharashtra":       {2018: 39.2, 2019: 39.8, 2020: 43.6, 2021: 42.6, 2022: 43.6, 2023: 45.3, 2024: 45.3},
    "Manipur":           {2018: 32.1, 2019: 32.9, 2020: 33.8, 2021: 30.5, 2022: 29.8, 2023: 35.5, 2024: 41.7},
    "Meghalaya":         {2018: 41.5, 2019: 41.1, 2020: 37.2, 2021: 38.7, 2022: 38.6, 2023: 41.2, 2024: 47.6},
    "Mizoram":           {2018: 36.0, 2019: 36.7, 2020: 41.4, 2021: 43.4, 2022: 36.8, 2023: 40.7, 2024: 39.5},
    "Nagaland":          {2018: 25.9, 2019: 28.5, 2020: 35.3, 2021: 38.6, 2022: 40.6, 2023: 45.8, 2024: 45.7},
    "Odisha":            {2018: 33.8, 2019: 35.7, 2020: 39.5, 2021: 41.7, 2022: 39.5, 2023: 44.4, 2024: 47.9},
    "Puducherry":        {2018: 30.1, 2019: 39.3, 2020: 37.3, 2021: 38.5, 2022: 40.4, 2023: 40.1, 2024: 41.1},
    "Punjab":            {2018: 33.8, 2019: 34.6, 2020: 37.8, 2021: 37.0, 2022: 38.6, 2023: 39.7, 2024: 41.3},
    "Rajasthan":         {2018: 34.2, 2019: 35.8, 2020: 39.4, 2021: 40.3, 2022: 40.6, 2023: 43.4, 2024: 45.3},
    "Sikkim":            {2018: 47.0, 2019: 49.4, 2020: 55.9, 2021: 60.5, 2022: 57.0, 2023: 60.9, 2024: 60.2},
    "Tamil Nadu":        {2018: 40.5, 2019: 41.2, 2020: 44.2, 2021: 46.0, 2022: 44.6, 2023: 44.0, 2024: 45.6},
    "Telangana":         {2018: 39.3, 2019: 40.1, 2020: 44.8, 2021: 46.0, 2022: 45.3, 2023: 45.1, 2024: 45.7},
    "Tripura":           {2018: 33.8, 2019: 34.1, 2020: 38.9, 2021: 41.9, 2022: 40.2, 2023: 43.9, 2024: 49.2},
    "Uttarakhand":       {2018: 30.7, 2019: 31.2, 2020: 38.1, 2021: 37.4, 2022: 37.6, 2023: 40.6, 2024: 44.2},
    "Uttar Pradesh":     {2018: 28.7, 2019: 28.7, 2020: 31.7, 2021: 34.5, 2022: 35.1, 2023: 37.8, 2024: 39.2},
    "West Bengal":       {2018: 37.3, 2019: 38.6, 2020: 39.2, 2021: 42.4, 2022: 41.7, 2023: 44.1, 2024: 46.4},
}

# All-India WPR (for normalization)
ALL_INDIA_WPR = {2018: 34.7, 2019: 35.3, 2020: 38.2, 2021: 39.8, 2022: 39.6, 2023: 41.1, 2024: 43.7}

# State × NCO division wages (Rs./month, rural+urban person, regular wage/salary)
# Extracted from PLFS Table 55 (PDF pdfplumber extraction)
# Only 3 years available (2019-20, 2020-21, 2021-22)
PLFS_STATE_WAGES: dict[int, dict[str, dict[str, float]]] = {}

def _load_state_wages() -> None:
    """Load extracted state wages from JSON file if available.

    Normalizes state names from PDF-extracted format to match CENSUS_2011_POP keys:
    - "Jammu & Kashmir" → "Jammu and Kashmir"
    - "Andaman & Nicobar Islands" → "Andaman and Nicobar Islands"
    - "Dadra & Nagar Haveli" + "Daman & Diu" → merged into
      "Dadra and Nagar Haveli and Daman and Diu" (population-weighted average)
    """
    global PLFS_STATE_WAGES
    wage_path = (Path(__file__).resolve().parent.parent.parent
                 / "data" / "raw" / "plfs_state_wages.json")
    if not wage_path.exists():
        return

    import json as _json
    with open(wage_path) as f:
        raw = _json.load(f)

    # Convert string year keys to int and normalize state names
    for year_str, states in raw.items():
        year = int(year_str)
        normalized: dict[str, dict[str, float]] = {}
        dnh_wages = None  # Dadra & Nagar Haveli
        dd_wages = None   # Daman & Diu
        for name, wages in states.items():
            canon = name.replace(" & ", " and ")
            if canon == "Dadra and Nagar Haveli":
                dnh_wages = wages
            elif canon == "Daman and Diu":
                dd_wages = wages
            else:
                normalized[canon] = wages
        # Merge D&NH + D&D with population-weighted average
        if dnh_wages or dd_wages:
            merged = {}
            dnh_pop, dd_pop = 0.343, 0.243  # Census 2011
            for did in [str(i) for i in range(1, 10)]:
                w1 = (dnh_wages or {}).get(did)
                w2 = (dd_wages or {}).get(did)
                if w1 is not None and w2 is not None:
                    merged[did] = (w1 * dnh_pop + w2 * dd_pop) / (dnh_pop + dd_pop)
                elif w1 is not None:
                    merged[did] = w1
                elif w2 is not None:
                    merged[did] = w2
            if merged:
                normalized["Dadra and Nagar Haveli and Daman and Diu"] = merged
        PLFS_STATE_WAGES[year] = normalized


def _compute_state_employment(active_years: list[int],
                              ilostat_totals: dict[int, float]
                              ) -> dict[str, dict[int, float]]:
    """Compute state total employment for each year.

    Uses Census 2011 population × state WPR as proportional weights,
    then normalizes so state sum equals ILOSTAT total for each year.
    """
    state_emp: dict[str, dict[int, float]] = {}

    for year in active_years:
        total_india = ilostat_totals.get(year)
        if not total_india:
            continue

        # Compute raw weights: pop × WPR for each state
        raw_weights: dict[str, float] = {}
        for state_name, pop in CENSUS_2011_POP.items():
            wpr = STATE_WPR.get(state_name, {}).get(year)
            if wpr is not None:
                raw_weights[state_name] = pop * wpr / 100.0

        # Normalize to match ILOSTAT total
        weight_sum = sum(raw_weights.values())
        if weight_sum <= 0:
            continue

        for state_name, raw_w in raw_weights.items():
            state_total = total_india * (raw_w / weight_sum)
            if state_name not in state_emp:
                state_emp[state_name] = {}
            state_emp[state_name][year] = state_total

    return state_emp


def export_plfs() -> None:
    """Export PLFS India time-series JSON file.

    National: uses PLFS % distributions (MoSPI API) scaled by ILOSTAT total.
    States: uses Census pop × WPR proportional weights, national NCO %,
            and state-specific wages where available (3 years from PDF Table 55).
    GDP = employment × monthly_wage × 12 (where wage data available).
    """
    print(f"\n=== PLFS India Time Series ===\n")

    # Load state wages from extracted PDF data
    _load_state_wages()
    if PLFS_STATE_WAGES:
        print(f"  Loaded state wages for years: "
              f"{sorted(PLFS_STATE_WAGES.keys())}")

    # Read ILOSTAT India data to get total employment per year
    ilostat_path = config.PUBLIC_DATA_DIR / "timeseries-ilostat-in.json"
    if not ilostat_path.exists():
        print("  ERROR: Run ILOSTAT export first (need total employment)")
        return

    with open(ilostat_path) as f:
        ilostat = json.load(f)

    # Compute total employment per year from ILOSTAT
    ilostat_years = ilostat["metadata"]["years"]
    region_data = ilostat["data"]["national-india"]
    ilostat_totals = {}
    for yi, year in enumerate(ilostat_years):
        total = 0
        for gdata in region_data.values():
            emp = gdata["emp"][yi]
            if emp is not None:
                total += emp
        if total > 0:
            ilostat_totals[year] = total

    # Map PLFS fiscal years to calendar years and compute absolute employment
    plfs_years = sorted(PLFS_PERCENTAGES.keys())

    # --- National data ---
    national_ts: dict = {}
    for div in NCO_DIVISIONS:
        national_ts[div["id"]] = {"emp": [], "gdp": []}

    active_years = []
    has_any_gdp = False
    for year in plfs_years:
        total_emp = ilostat_totals.get(year)
        if total_emp is None:
            print(f"  WARNING: No ILOSTAT total for {year}, skipping")
            continue
        active_years.append(year)
        pcts = PLFS_PERCENTAGES[year]
        wages = PLFS_WAGES.get(year)
        for div in NCO_DIVISIONS:
            did = div["id"]
            pct = pcts.get(did, 0)
            emp = round(total_emp * pct / 100)
            national_ts[did]["emp"].append(emp)
            if wages and did in wages:
                gdp = round(emp * wages[did] * 12)
                national_ts[did]["gdp"].append(gdp)
                has_any_gdp = True
            else:
                national_ts[did]["gdp"].append(None)
        fy = f"{year - 1}-{str(year)[-2:]}"
        gdp_flag = " (with wages)" if wages else " (no wages)"
        print(f"  {fy}: total={total_emp:,.0f}{gdp_flag}")

    if not active_years:
        print("  ERROR: No valid years found")
        return

    # Strip empty GDP arrays
    for did in national_ts:
        if not any(v is not None for v in national_ts[did]["gdp"]):
            del national_ts[did]["gdp"]

    # --- State data ---
    print(f"\n  Computing state employment...")
    state_emp = _compute_state_employment(active_years, ilostat_totals)
    print(f"  States with data: {len(state_emp)}")

    all_data = {"national-india": national_ts}
    regions = [{
        "regionId": "national-india",
        "name": "India",
        "regionType": "National",
    }]

    for state_name in sorted(state_emp.keys()):
        region_id = _make_region_id("State", state_name)
        regions.append({
            "regionId": region_id,
            "name": state_name,
            "regionType": "State",
        })

        state_ts: dict = {}
        for div in NCO_DIVISIONS:
            state_ts[div["id"]] = {"emp": [], "gdp": []}

        state_has_gdp = False
        for yi, year in enumerate(active_years):
            state_total = state_emp[state_name].get(year)
            pcts = PLFS_PERCENTAGES[year]

            # If state has no WPR for this year, emit None for all divisions
            if state_total is None or state_total <= 0:
                for div in NCO_DIVISIONS:
                    state_ts[div["id"]]["emp"].append(None)
                    state_ts[div["id"]]["gdp"].append(None)
                continue

            # Wages: prefer state-specific, fallback to national
            state_wages = PLFS_STATE_WAGES.get(year, {}).get(state_name)
            national_wages = PLFS_WAGES.get(year)

            for div in NCO_DIVISIONS:
                did = div["id"]
                pct = pcts.get(did, 0)
                emp = round(state_total * pct / 100)
                state_ts[did]["emp"].append(emp)

                # GDP: use state wage if available, else national
                wage = None
                if state_wages and did in state_wages:
                    wage = state_wages[did]
                elif national_wages and did in national_wages:
                    wage = national_wages[did]

                if wage is not None and wage > 0:
                    gdp = round(emp * wage * 12)
                    state_ts[did]["gdp"].append(gdp)
                    state_has_gdp = True
                    has_any_gdp = True
                else:
                    state_ts[did]["gdp"].append(None)

        # Strip empty GDP arrays
        for did in state_ts:
            if not any(v is not None for v in state_ts[did]["gdp"]):
                del state_ts[did]["gdp"]

        all_data[region_id] = state_ts

    # Build output
    groups = [
        {"id": d["id"], "name": d["name"], "color": NCO_COLORS.get(d["id"], "#999")}
        for d in NCO_DIVISIONS
    ]

    output = {
        "metadata": {
            "source": "PLFS Annual Reports",
            "country": "in",
            "years": active_years,
            "hasGdp": has_any_gdp,
        },
        "groups": groups,
        "regions": regions,
        "data": all_data,
    }

    out_path = config.PUBLIC_DATA_DIR / "timeseries-plfs-in.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))
    print(f"\n  Output: {out_path.name} ({len(groups)} groups, "
          f"{len(active_years)} years, {len(regions)} regions, "
          f"GDP={'yes' if has_any_gdp else 'no'})")
    print(f"  Done.")


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Export time-series JSON for the frontend"
    )
    parser.add_argument(
        "--source", choices=["oes", "ilostat", "plfs", "all"], default="all",
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

    if args.source in ("plfs", "all"):
        export_plfs()


if __name__ == "__main__":
    main()
