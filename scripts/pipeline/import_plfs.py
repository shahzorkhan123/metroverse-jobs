"""Import India PLFS data from pre-extracted CSV tables.

Data sources:
  - Table 25: NCO 1-3 digit percentage distribution of workers (PLFS 2023-24)
  - Table 50: Average monthly wages by 1-digit NCO division (PLFS 2023-24)
"""

import csv
import sqlite3
from pathlib import Path

from . import config, db


def _read_table25(csv_path: Path) -> list[dict]:
    """Read NCO distribution CSV (Table 25).

    Returns list of dicts with keys: nco_code, name, pct
    """
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "nco_code": row["nco_code"].strip(),
                "name": row["name"].strip(),
                "pct": float(row["pct_rural_urban_person"]),
            })
    return rows


def _read_table50(csv_path: Path) -> dict[str, int]:
    """Read NCO wages CSV (Table 50).

    Returns dict mapping 1-digit NCO division -> monthly wage (Rs.)
    """
    wages = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            div = row["nco_division"].strip()
            wages[div] = int(row["avg_monthly_wage_rural_urban_person"])
    return wages


def _nco_level(code: str) -> int:
    """NCO hierarchy: level = number of digits."""
    return len(code.strip())


def _nco_division(code: str) -> str:
    """Get the 1-digit division for any NCO code."""
    return code[0]


def import_india_national(conn: sqlite3.Connection, year: int = 2024) -> int:
    """Import India national data from Table 25 + Table 50 CSVs.

    Steps:
    1. Read percentage distribution (Table 25)
    2. Read wages by division (Table 50)
    3. Convert percentages to estimated worker counts
    4. Assign wages (Table 50 for level 1; inherit parent division for levels 2-3)
    5. Calculate GDP = totEmp * monthly_wage * 12
    6. Insert into SQLite
    """
    ind_config = config.COUNTRIES["IND"]
    table25_path = ind_config["table25_csv"]
    table50_path = ind_config["table50_csv"]
    total_workers = ind_config["total_workers"]

    if not table25_path.exists():
        raise FileNotFoundError(f"Table 25 CSV not found: {table25_path}")
    if not table50_path.exists():
        raise FileNotFoundError(f"Table 50 CSV not found: {table50_path}")

    # Read source data
    distributions = _read_table25(table25_path)
    wages = _read_table50(table50_path)

    # Create country and region
    country_id = db.ensure_country(conn, "IND", "India", "NCO", "INR")
    region_id = db.ensure_region(conn, country_id, "India", "National")

    count = 0
    for dist in distributions:
        code = dist["nco_code"]
        name = dist["name"]
        pct = dist["pct"]

        # Calculate employment from percentage
        employment = round(total_workers * pct / 100.0)
        if employment <= 0:
            continue

        # Get wage: Table 50 for 1-digit, inherit parent division for 2-3 digit
        division = _nco_division(code)
        monthly_wage = wages.get(division, 0)

        # Get major group name
        major_group_name = config.NCO_MAJOR_GROUPS.get(division, f"Division {division}")

        # Insert record (wage is monthly, stored as-is; GDP = emp * monthly * 12)
        gdp = employment * monthly_wage * 12
        conn.execute(
            "INSERT OR REPLACE INTO occupations "
            "(year, region_id, occupation_code, occupation_title, "
            "major_group_name, employment, mean_annual_wage, gdp, complexity_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.5)",
            (year, region_id, code, name,
             major_group_name, employment, monthly_wage, gdp),
        )
        count += 1

    conn.commit()
    return count


def import_all_india(conn: sqlite3.Connection, year: int = 2024) -> int:
    """Orchestrate India data import.

    Returns total records imported.
    """
    print(f"Importing India PLFS data for year {year}...")

    count = import_india_national(conn, year)
    print(f"  National: {count} occupation records")

    # Compute complexity scores (min-max normalized GDP per region)
    print("  Computing complexity scores...")
    db.compute_complexity_scores(conn)

    return count
