"""Validation checks on the database and generated output."""

import json
import re
import sqlite3
from pathlib import Path

from . import config

SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")
ISCO_PATTERN = re.compile(r"^OC\d$")
VALID_REGION_TYPES = {"National", "State", "Metro"}


def validate_db(conn: sqlite3.Connection) -> list[str]:
    """Run validation checks on the SQLite database. Returns list of errors."""
    errors = []

    # Check we have records
    count = conn.execute("SELECT COUNT(*) FROM occupations").fetchone()[0]
    if count == 0:
        errors.append("No occupation records in database")
        return errors

    # Check region types
    region_types = conn.execute(
        "SELECT DISTINCT region_type FROM regions"
    ).fetchall()
    for (rt,) in region_types:
        if rt not in VALID_REGION_TYPES:
            errors.append(f"Invalid region_type: {rt}")

    # Check for negative employment
    bad = conn.execute(
        "SELECT COUNT(*) FROM occupations WHERE employment <= 0"
    ).fetchone()[0]
    if bad > 0:
        errors.append(f"{bad} records have non-positive employment")

    # Check for negative wages
    bad = conn.execute(
        "SELECT COUNT(*) FROM occupations WHERE mean_annual_wage <= 0"
    ).fetchone()[0]
    if bad > 0:
        errors.append(f"{bad} records have non-positive wages")

    # Check GDP = employment * wage
    bad = conn.execute("""
        SELECT COUNT(*) FROM occupations
        WHERE ABS(gdp - employment * mean_annual_wage) > 1
    """).fetchone()[0]
    if bad > 0:
        errors.append(f"{bad} records have GDP != employment * wage")

    # Check complexity_score range
    bad = conn.execute("""
        SELECT COUNT(*) FROM occupations
        WHERE complexity_score < 0 OR complexity_score > 1
    """).fetchone()[0]
    if bad > 0:
        errors.append(f"{bad} records have complexity_score outside [0, 1]")

    # Check for duplicate occupation codes within same year/region
    dupes = conn.execute("""
        SELECT year, region_id, occupation_code, COUNT(*) as cnt
        FROM occupations
        GROUP BY year, region_id, occupation_code
        HAVING cnt > 1
    """).fetchall()
    if dupes:
        errors.append(f"{len(dupes)} duplicate year/region/code combinations")

    return errors


def validate_jsonp(jsonp_path: Path | None = None) -> list[str]:
    """Validate the generated job_data.js file. Returns list of errors."""
    if jsonp_path is None:
        jsonp_path = config.JSONP_PATH

    errors = []

    if not jsonp_path.exists():
        errors.append(f"JSONP file not found: {jsonp_path}")
        return errors

    content = jsonp_path.read_text(encoding="utf-8")

    if "window.BLS_DATA" not in content:
        errors.append("JSONP file missing window.BLS_DATA")

    if "jobData:" not in content:
        errors.append("JSONP file missing jobData array")

    # Extract and parse the jobData array
    match = re.search(r"jobData:\s*(\[.*?\])\s*,", content, re.DOTALL)
    if not match:
        errors.append("Could not extract jobData array from JSONP")
        return errors

    try:
        records = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        errors.append(f"jobData is not valid JSON: {e}")
        return errors

    if len(records) == 0:
        errors.append("jobData array is empty")
        return errors

    # Validate each record
    required_fields = [
        "year", "Region_Type", "Region", "SOC_Code", "OCC_TITLE",
        "SOC_Major_Group_Name", "TOT_EMP", "A_MEAN", "GDP",
        "complexity_score",
    ]
    for i, record in enumerate(records):
        for field in required_fields:
            if field not in record:
                errors.append(f"Record {i} missing field '{field}'")
                break

        if "Region_Type" in record:
            if record["Region_Type"] not in VALID_REGION_TYPES:
                errors.append(
                    f"Record {i} invalid Region_Type: {record['Region_Type']}"
                )

        if "complexity_score" in record:
            cs = record["complexity_score"]
            if not (0 <= cs <= 1):
                errors.append(
                    f"Record {i} complexity_score out of range: {cs}"
                )

    return errors


def validate_json(json_path: Path | None = None) -> list[str]:
    """Validate the generated bls-data.json file. Returns list of errors."""
    if json_path is None:
        json_path = config.JSON_FULL_PATH

    errors = []

    if not json_path.exists():
        errors.append(f"JSON file not found: {json_path}")
        return errors

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return errors

    # Check required top-level keys
    for key in ["metadata", "regions", "occupations", "majorGroups", "regionData"]:
        if key not in data:
            errors.append(f"Missing top-level key: {key}")

    if "metadata" in data:
        meta = data["metadata"]
        if "years" not in meta:
            errors.append("metadata missing 'years'")
        if "lastUpdated" not in meta:
            errors.append("metadata missing 'lastUpdated'")

    if "regions" in data and len(data["regions"]) == 0:
        errors.append("regions array is empty")

    if "occupations" in data and len(data["occupations"]) == 0:
        errors.append("occupations array is empty")

    if "regionData" in data and len(data["regionData"]) == 0:
        errors.append("regionData is empty")

    return errors
