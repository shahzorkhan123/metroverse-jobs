"""Generate intermediate CSV files for Excel analysis."""

import csv
import sqlite3
from pathlib import Path

from . import config

COLUMNS = [
    "country", "year", "region_type", "region", "occupation_code",
    "occupation_title", "major_group_name", "employment",
    "mean_annual_wage", "gdp", "complexity_score",
]


def _query_all(conn: sqlite3.Connection) -> list[tuple]:
    """Query all occupation records with joined country/region info."""
    return conn.execute("""
        SELECT c.name, o.year, r.region_type, r.name,
               o.occupation_code, o.occupation_title, o.major_group_name,
               o.employment, o.mean_annual_wage, o.gdp, o.complexity_score
        FROM occupations o
        JOIN regions r ON o.region_id = r.id
        JOIN countries c ON r.country_id = c.id
        ORDER BY c.name, r.region_type, r.name, o.occupation_code
    """).fetchall()


def _write_csv(filepath: Path, rows: list[tuple],
               columns: list[str] = COLUMNS) -> int:
    """Write rows to a CSV file. Returns row count."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    return len(rows)


def export_all(conn: sqlite3.Connection) -> dict[str, int]:
    """Generate all intermediate CSVs. Returns dict of filename -> row count."""
    export_dir = config.EXPORT_DIR
    all_rows = _query_all(conn)

    results = {}

    # Combined data (everything)
    count = _write_csv(export_dir / "combined_data.csv", all_rows)
    results["combined_data.csv"] = count

    # US National only
    us_national = [r for r in all_rows
                   if r[0] == "United States" and r[2] == "National"]
    count = _write_csv(export_dir / "us_national.csv", us_national)
    results["us_national.csv"] = count

    # US by State
    us_states = [r for r in all_rows
                 if r[0] == "United States" and r[2] == "State"]
    count = _write_csv(export_dir / "us_by_state.csv", us_states)
    results["us_by_state.csv"] = count

    # US by Metro
    us_metros = [r for r in all_rows
                 if r[0] == "United States" and r[2] == "Metro"]
    count = _write_csv(export_dir / "us_by_metro.csv", us_metros)
    results["us_by_metro.csv"] = count

    # Country summary
    summary_rows = conn.execute("""
        SELECT c.name, c.code, COUNT(DISTINCT r.id) as regions,
               COUNT(o.id) as occupations,
               SUM(o.employment) as total_employment,
               SUM(o.gdp) as total_gdp
        FROM countries c
        LEFT JOIN regions r ON r.country_id = c.id
        LEFT JOIN occupations o ON o.region_id = r.id
        GROUP BY c.code
        ORDER BY c.name
    """).fetchall()
    summary_cols = ["country", "code", "regions", "occupations",
                    "total_employment", "total_gdp"]
    count = _write_csv(export_dir / "country_summary.csv",
                       summary_rows, summary_cols)
    results["country_summary.csv"] = count

    return results
