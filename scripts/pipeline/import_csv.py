"""CSV parsing, code system detection, and import logic."""

import csv
import re
import sqlite3
from pathlib import Path

from . import config, db

SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")
ISCO_PATTERN = re.compile(r"^OC\d$")


def detect_code_system(code: str) -> str:
    """Detect whether an occupation code is SOC or ISCO."""
    if SOC_PATTERN.match(code):
        return "SOC"
    if ISCO_PATTERN.match(code):
        return "ISCO"
    raise ValueError(f"Unknown occupation code format: {code}")


def derive_major_group(code: str, title: str, code_system: str) -> str:
    """Derive major group name from occupation code.

    SOC: lookup by 2-digit prefix in SOC_MAJOR_GROUPS.
    ISCO: the occupation title IS the group name.
    """
    if code_system == "SOC":
        prefix = code[:2]
        return config.SOC_MAJOR_GROUPS.get(prefix, title)
    # ISCO: title is the group
    return title


def read_csv(csv_path: Path) -> list[dict]:
    """Read a CSV file and return list of row dicts.

    Expected columns: occupation_code, occupation_title, employment,
                      mean_annual_wage, complexity_score
    """
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "occupation_code": row["occupation_code"].strip(),
                "occupation_title": row["occupation_title"].strip(),
                "employment": int(float(row["employment"])),
                "mean_annual_wage": int(float(row["mean_annual_wage"])),
            })
    return rows


def import_records(conn: sqlite3.Connection, rows: list[dict],
                   region_id: int, year: int, code_system: str) -> int:
    """Import parsed CSV rows into the occupations table. Returns count."""
    count = 0
    for row in rows:
        major_group = derive_major_group(
            row["occupation_code"], row["occupation_title"], code_system
        )
        db.insert_occupation(
            conn,
            year=year,
            region_id=region_id,
            occupation_code=row["occupation_code"],
            occupation_title=row["occupation_title"],
            major_group_name=major_group,
            employment=row["employment"],
            mean_annual_wage=row["mean_annual_wage"],
        )
        count += 1
    return count


def import_national(conn: sqlite3.Connection, country_code: str,
                    year: int) -> int:
    """Import one country's national CSV. Returns record count."""
    country_cfg = config.COUNTRIES[country_code]
    csv_path = country_cfg["national_csv"]
    if not csv_path.exists():
        print(f"  Skipping {country_code} national: {csv_path} not found")
        return 0

    country_id = db.ensure_country(
        conn, country_code, country_cfg["name"],
        country_cfg["code_system"], country_cfg.get("currency", "USD"),
    )
    region_id = db.ensure_region(
        conn, country_id, country_cfg["national_region_name"], "National"
    )

    rows = read_csv(csv_path)
    count = import_records(conn, rows, region_id, year,
                           country_cfg["code_system"])
    print(f"  {country_code} National: {count} records")
    return count


def import_states(conn: sqlite3.Connection, country_code: str,
                  year: int) -> int:
    """Import all state CSVs for a country. Returns total record count."""
    country_cfg = config.COUNTRIES[country_code]
    states_dir = country_cfg.get("states_dir")
    if not states_dir or not states_dir.exists():
        return 0

    country_id = db.ensure_country(
        conn, country_code, country_cfg["name"],
        country_cfg["code_system"], country_cfg.get("currency", "USD"),
    )

    total = 0
    for csv_path in sorted(states_dir.glob("*_occupational_data.csv")):
        stem = csv_path.stem.replace("_occupational_data", "")
        display_name = config.display_name_for_state(stem)
        region_id = db.ensure_region(conn, country_id, display_name, "State")
        rows = read_csv(csv_path)
        count = import_records(conn, rows, region_id, year,
                               country_cfg["code_system"])
        total += count

    if total > 0:
        print(f"  {country_code} States: {total} records "
              f"({len(list(states_dir.glob('*_occupational_data.csv')))} files)")
    return total


def import_metros(conn: sqlite3.Connection, year: int) -> int:
    """Import all metro CSVs. Maps each to the correct country. Returns count."""
    metros_dir = config.DATA_DIR / "metros"
    if not metros_dir.exists():
        return 0

    total = 0
    for csv_path in sorted(metros_dir.glob("*_occupational_data.csv")):
        stem = config.metro_stem(csv_path.name)
        country_code = config.country_for_metro(stem)
        country_cfg = config.COUNTRIES[country_code]

        country_id = db.ensure_country(
            conn, country_code, country_cfg["name"],
            country_cfg["code_system"], country_cfg.get("currency", "USD"),
        )

        display_name = config.display_name_for_metro(stem)
        region_id = db.ensure_region(conn, country_id, display_name, "Metro")
        rows = read_csv(csv_path)
        count = import_records(conn, rows, region_id, year,
                               country_cfg["code_system"])
        total += count

    if total > 0:
        metro_count = len(list(metros_dir.glob("*_occupational_data.csv")))
        print(f"  Metros: {total} records ({metro_count} files)")
    return total


def import_combined_csv(conn: sqlite3.Connection, csv_path: Path,
                        year: int) -> int:
    """Import a combined CSV with region_type and region columns.

    Expected columns: year, region_type, region, occupation_code,
                      occupation_title, major_group_name, employment,
                      mean_annual_wage
    """
    country_code = "USA"
    country_cfg = config.COUNTRIES[country_code]
    country_id = db.ensure_country(
        conn, country_code, country_cfg["name"],
        country_cfg["code_system"], country_cfg.get("currency", "USD"),
    )

    total = 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            region_type = row["region_type"].strip()
            region_name = row["region"].strip()
            region_id = db.ensure_region(conn, country_id, region_name, region_type)
            db.insert_occupation(
                conn,
                year=int(row.get("year", year)),
                region_id=region_id,
                occupation_code=row["occupation_code"].strip(),
                occupation_title=row["occupation_title"].strip(),
                major_group_name=row["major_group_name"].strip(),
                employment=int(float(row["employment"])),
                mean_annual_wage=int(float(row["mean_annual_wage"])),
            )
            total += 1

    print(f"  Combined CSV: {total} records from {csv_path.name}")
    return total


def import_all(conn: sqlite3.Connection, year: int) -> int:
    """Import everything: all countries' national + states + metros."""
    total = 0

    # National data for each country
    for country_code in config.COUNTRIES:
        total += import_national(conn, country_code, year)

    # State data (currently only USA has states)
    for country_code in config.COUNTRIES:
        total += import_states(conn, country_code, year)

    # Metro data (auto-mapped to countries)
    total += import_metros(conn, year)

    return total
