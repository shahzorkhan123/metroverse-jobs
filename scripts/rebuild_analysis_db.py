"""
rebuild_analysis_db.py
======================
Rebuilds data/analysis.db from all public/data/*.json files.
This is a read-only mirror for analytical queries — it does NOT affect
the website data pipeline or data/bls.db.

Usage:
    python scripts/rebuild_analysis_db.py           # drop + rebuild
    python scripts/rebuild_analysis_db.py --verify  # rebuild + run sanity checks
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "public" / "data"
DB_PATH = ROOT / "data" / "analysis.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE datasets (
    dataset_id      TEXT PRIMARY KEY,
    country_code    TEXT NOT NULL,
    source          TEXT NOT NULL,
    classification  TEXT NOT NULL,
    description     TEXT,
    year_range      TEXT
);

CREATE TABLE regions (
    region_id        TEXT PRIMARY KEY,
    country_code     TEXT NOT NULL,
    name             TEXT NOT NULL,
    region_type      TEXT NOT NULL,
    state_abbr       TEXT
);

CREATE TABLE occupations (
    occupation_key    TEXT PRIMARY KEY,
    dataset_id        TEXT NOT NULL REFERENCES datasets(dataset_id),
    code              TEXT NOT NULL,
    title             TEXT NOT NULL,
    level             INTEGER NOT NULL,
    major_group_code  TEXT,
    major_group_name  TEXT
);

CREATE TABLE occupation_year_stats (
    dataset_id       TEXT NOT NULL,
    region_id        TEXT NOT NULL,
    occupation_key   TEXT NOT NULL,
    year             INTEGER NOT NULL,
    employment       REAL,
    mean_annual_wage REAL,
    gdp              REAL,
    is_synthetic     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (dataset_id, region_id, occupation_key, year)
);

CREATE INDEX idx_oys_region ON occupation_year_stats(region_id, year);
CREATE INDEX idx_oys_occ    ON occupation_year_stats(occupation_key, year);
CREATE INDEX idx_oys_ds     ON occupation_year_stats(dataset_id, year);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def upsert_region(cur, region_id, country_code, name, region_type, state_abbr=None):
    cur.execute(
        "INSERT OR IGNORE INTO regions VALUES (?,?,?,?,?)",
        (region_id, country_code, name, region_type, state_abbr),
    )


def upsert_occupation(cur, occ_key, dataset_id, code, title, level,
                      major_group_code=None, major_group_name=None):
    cur.execute(
        "INSERT OR IGNORE INTO occupations VALUES (?,?,?,?,?,?,?)",
        (occ_key, dataset_id, code, title, level, major_group_code, major_group_name),
    )


# ---------------------------------------------------------------------------
# Ingest: snapshot files  (bls-data-{country}-2024*.json)
# ---------------------------------------------------------------------------

def ingest_snapshot(cur, path, country_code, dataset_id):
    data = load_json(path)
    rows_inserted = 0

    # Determine year from metadata
    year = data.get("metadata", {}).get("year", 2024)

    # Register occupations
    for occ in data.get("occupations", []):
        code = occ.get("socCode") or occ.get("code", "")
        title = occ.get("name") or occ.get("title", "")
        level = occ.get("level", 1)
        mg_code = occ.get("majorGroupId") or occ.get("majorGroupCode")
        mg_name = occ.get("majorGroupName")
        occ_key = f"{dataset_id}:{code}"
        upsert_occupation(cur, occ_key, dataset_id, code, title, level, mg_code, mg_name)

    # Register regions
    state_abbrs = {}
    # Try to load from meta catalog
    meta_path = DATA_DIR / "bls-data.json"
    if meta_path.exists():
        meta = load_json(meta_path)
        cm = meta.get("countryMetadata", {}).get(country_code, {})
        state_abbrs = cm.get("stateAbbreviations", {})

    for reg in data.get("regions", []):
        rid = reg.get("regionId", "")
        name = reg.get("name", "")
        rtype = reg.get("regionType", "")
        abbr = state_abbrs.get(name)
        upsert_region(cur, rid, country_code, name, rtype, abbr)

    # Ingest occupation_year_stats
    region_data = data.get("regionData", {})
    for region_id, year_map in region_data.items():
        for yr_key, occ_list in year_map.items():
            try:
                yr = int(yr_key)
            except ValueError:
                continue
            if not isinstance(occ_list, list):
                continue
            for entry in occ_list:
                code = entry.get("socCode") or entry.get("code", "")
                if not code:
                    continue
                occ_key = f"{dataset_id}:{code}"
                emp = entry.get("totEmp") or entry.get("employment")
                wage = entry.get("aMean") or entry.get("meanWage") or entry.get("mean_annual_wage")
                gdp = entry.get("gdp")
                cur.execute(
                    "INSERT OR REPLACE INTO occupation_year_stats "
                    "(dataset_id, region_id, occupation_key, year, employment, mean_annual_wage, gdp, is_synthetic) "
                    "VALUES (?,?,?,?,?,?,?,0)",
                    (dataset_id, region_id, occ_key, yr, emp, wage, gdp),
                )
                rows_inserted += 1

    return rows_inserted


# ---------------------------------------------------------------------------
# Ingest: time-series files  (timeseries-*.json)
# ---------------------------------------------------------------------------

def ingest_timeseries(cur, path, country_code, dataset_id, source, classification):
    data = load_json(path)
    rows_inserted = 0

    years = data.get("metadata", {}).get("years", [])
    groups = data.get("groups", [])
    regions_list = data.get("regions", [])
    ts_data = data.get("data", {})

    year_range = f"{years[0]}-{years[-1]}" if years else ""

    # Update dataset year_range
    cur.execute(
        "UPDATE datasets SET year_range=? WHERE dataset_id=?",
        (year_range, dataset_id),
    )

    # Load state abbreviations
    state_abbrs = {}
    meta_path = DATA_DIR / "bls-data.json"
    if meta_path.exists():
        meta = load_json(meta_path)
        cm = meta.get("countryMetadata", {}).get(country_code, {})
        state_abbrs = cm.get("stateAbbreviations", {})

    # Register occupations (groups)
    for grp in groups:
        gid = str(grp.get("id", ""))
        title = grp.get("name", "")
        occ_key = f"{dataset_id}:{gid}"
        upsert_occupation(cur, occ_key, dataset_id, gid, title, 1,
                          major_group_code=gid, major_group_name=title)

    # Register regions
    for reg in regions_list:
        rid = reg.get("regionId", "")
        name = reg.get("name", "")
        rtype = reg.get("regionType", "")
        abbr = state_abbrs.get(name)
        upsert_region(cur, rid, country_code, name, rtype, abbr)

    # Determine which region_ids are states (for synthetic flagging)
    state_region_ids = {
        r.get("regionId") for r in regions_list if r.get("regionType") == "State"
    }

    # Ingest stats — state rows for plfs_in are now REAL (from PLFS microdata per year)
    for region_id, group_map in ts_data.items():

        for gid, metrics in group_map.items():
            occ_key = f"{dataset_id}:{gid}"
            emp_series = metrics.get("emp", [])
            gdp_series = metrics.get("gdp", [])

            for i, yr in enumerate(years):
                emp = emp_series[i] if i < len(emp_series) else None
                gdp = gdp_series[i] if i < len(gdp_series) else None
                # gdp may be 0 meaning "not available" in some sources
                if gdp == 0:
                    gdp = None

                cur.execute(
                    "INSERT OR REPLACE INTO occupation_year_stats "
                    "(dataset_id, region_id, occupation_key, year, employment, mean_annual_wage, gdp, is_synthetic) "
                    "VALUES (?,?,?,?,?,NULL,?,0)",
                    (dataset_id, region_id, occ_key, yr, emp, gdp),
                )
                rows_inserted += 1

    return rows_inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DATASETS = [
    # (dataset_id, country_code, source, classification, description)
    ("snapshot_us", "us", "snapshot", "SOC_2018",
     "US BLS OES 2024 cross-sectional snapshot (levels 1-4, national + state + metro)"),
    ("snapshot_in", "in", "snapshot", "NCO_2015",
     "India PLFS cross-sectional snapshots (2019, 2022, 2024) — real state × NCO data from microdata"),
    ("snapshot_in_2018", "in", "snapshot", "NCO_2015", "India PLFS 2017-18 microdata — real state × NCO"),
    ("snapshot_in_2019", "in", "snapshot", "NCO_2015", "India PLFS 2018-19 microdata — real state × NCO"),
    ("snapshot_in_2020", "in", "snapshot", "NCO_2015", "India PLFS 2019-20 microdata — real state × NCO"),
    ("snapshot_in_2021", "in", "snapshot", "NCO_2015", "India PLFS 2020-21 microdata — real state × NCO"),
    ("snapshot_in_2022", "in", "snapshot", "NCO_2015", "India PLFS 2021-22 microdata — real state × NCO"),
    ("snapshot_in_2023", "in", "snapshot", "NCO_2015", "India PLFS 2022-23 microdata — real state × NCO"),
    ("bls_oes_us", "us", "bls_oes", "SOC_2018",
     "US BLS OES time series (national + state + metro, SOC major groups)"),
    ("plfs_in", "in", "plfs", "NCO_2015",
     "India PLFS time series 2018-2024 (national + 36 states, NCO divisions, REAL microdata)."),
    ("ilostat_us", "us", "ilostat", "ISCO_08",
     "ILOSTAT US national time series 1991-2025 (ISCO-08 major groups)"),
    ("ilostat_in", "in", "ilostat", "ISCO_08",
     "ILOSTAT India national time series 1991-2025 (ISCO-08 major groups)"),
]

SNAPSHOT_FILES = [
    # (filename, country_code, dataset_id)
    ("bls-data-us-2024.json",       "us", "snapshot_us"),
    ("bls-data-us-2024-3.json",     "us", "snapshot_us"),
    ("bls-data-us-2024-4.json",     "us", "snapshot_us"),
    ("bls-data-in-2024.json",       "in", "snapshot_in"),
    ("bls-data-in-2024-3.json",     "in", "snapshot_in"),
    # Real microdata snapshots — all years from unit-level PLFS data
    ("bls-data-in-2018.json",       "in", "snapshot_in_2018"),
    ("bls-data-in-2018-3.json",     "in", "snapshot_in_2018"),
    ("bls-data-in-2019.json",       "in", "snapshot_in_2019"),
    ("bls-data-in-2019-3.json",     "in", "snapshot_in_2019"),
    ("bls-data-in-2020.json",       "in", "snapshot_in_2020"),
    ("bls-data-in-2020-3.json",     "in", "snapshot_in_2020"),
    ("bls-data-in-2021.json",       "in", "snapshot_in_2021"),
    ("bls-data-in-2021-3.json",     "in", "snapshot_in_2021"),
    ("bls-data-in-2022.json",       "in", "snapshot_in_2022"),
    ("bls-data-in-2022-3.json",     "in", "snapshot_in_2022"),
    ("bls-data-in-2023.json",       "in", "snapshot_in_2023"),
    ("bls-data-in-2023-3.json",     "in", "snapshot_in_2023"),
]

TIMESERIES_FILES = [
    # (filename, country_code, dataset_id, source, classification)
    ("timeseries-us-oes.json",      "us", "bls_oes_us", "bls_oes", "SOC_2018"),
    ("timeseries-us-oes-metro.json","us", "bls_oes_us", "bls_oes", "SOC_2018"),
    ("timeseries-plfs-in.json",     "in", "plfs_in",   "plfs",    "NCO_2015"),
    ("timeseries-ilostat-us.json",  "us", "ilostat_us","ilostat", "ISCO_08"),
    ("timeseries-ilostat-in.json",  "in", "ilostat_in","ilostat", "ISCO_08"),
]


def build(verify=False):
    print(f"Building {DB_PATH} ...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Drop and recreate
    cur.executescript("PRAGMA foreign_keys=OFF;")
    for tbl in ("occupation_year_stats", "occupations", "regions", "datasets"):
        cur.execute(f"DROP TABLE IF EXISTS {tbl}")
    for stmt in DDL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)

    # Insert dataset catalog
    for ds in DATASETS:
        cur.execute(
            "INSERT INTO datasets (dataset_id,country_code,source,classification,description) VALUES (?,?,?,?,?)",
            ds,
        )

    conn.commit()

    total_rows = 0

    # Ingest snapshots
    for fname, country, ds_id in SNAPSHOT_FILES:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"  [skip] {fname} not found")
            continue
        n = ingest_snapshot(cur, fpath, country, ds_id)
        print(f"  snapshot  {fname:<45} {n:>8,} rows")
        total_rows += n
        conn.commit()

    # Ingest time series
    for fname, country, ds_id, source, cls in TIMESERIES_FILES:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            print(f"  [skip] {fname} not found")
            continue
        n = ingest_timeseries(cur, fpath, country, ds_id, source, cls)
        print(f"  timeseries {fname:<44} {n:>8,} rows")
        total_rows += n
        conn.commit()

    # Summary
    print()
    for tbl in ("datasets", "regions", "occupations", "occupation_year_stats"):
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = cur.fetchone()[0]
        print(f"  {tbl:<30} {cnt:>10,} rows")

    print(f"\n  Total fact rows inserted: {total_rows:,}")

    if verify:
        run_verify(cur)

    conn.close()
    print(f"\nDone. DB written to {DB_PATH}")


def run_verify(cur):
    print("\n--- Verification ---")
    checks = [
        ("datasets >= 12",
         "SELECT COUNT(*) FROM datasets", lambda n: n >= 12),
        ("India states >= 36",
         "SELECT COUNT(*) FROM regions WHERE country_code='in' AND region_type='State'",
         lambda n: n >= 36),
        ("US states >= 50",
         "SELECT COUNT(*) FROM regions WHERE country_code='us' AND region_type='State'",
         lambda n: n >= 50),
        ("PLFS national rows present",
         "SELECT COUNT(*) FROM occupation_year_stats WHERE dataset_id='plfs_in' AND region_id='national-india'",
         lambda n: n >= 9 * 7 * 0.9),
        ("PLFS real state rows present",
         "SELECT COUNT(DISTINCT region_id) FROM occupation_year_stats "
         "WHERE dataset_id='plfs_in' AND region_id LIKE 'state-%'",
         lambda n: n >= 30),
        ("US BLS OES years >= 20",
         "SELECT COUNT(DISTINCT year) FROM occupation_year_stats WHERE dataset_id='bls_oes_us'",
         lambda n: n >= 20),
        ("ILOSTAT India years >= 30",
         "SELECT COUNT(DISTINCT year) FROM occupation_year_stats WHERE dataset_id='ilostat_in'",
         lambda n: n >= 30),
        ("Bihar snapshot employment 2024 > 0",
         "SELECT employment FROM occupation_year_stats "
         "WHERE dataset_id='snapshot_in' AND region_id='state-bihar' AND year=2024 LIMIT 1",
         lambda n: n is not None and n > 0),
    ]

    all_pass = True
    for label, sql, pred in checks:
        cur.execute(sql)
        row = cur.fetchone()
        val = row[0] if row else None
        ok = pred(val) if val is not None else False
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {label} (got {val})")

    if all_pass:
        print("\n  All checks passed.")
    else:
        print("\n  Some checks FAILED — inspect the output above.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild data/analysis.db from public/data JSONs")
    parser.add_argument("--verify", action="store_true", help="Run sanity checks after build")
    args = parser.parse_args()
    build(verify=args.verify)
