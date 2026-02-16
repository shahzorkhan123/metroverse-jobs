"""Generate split data files: data/meta.js + data/regions/*.data.js."""

import json
import re
import sqlite3
from pathlib import Path

from . import config


def _make_slug(region_type: str, region_name: str) -> str:
    """Generate a filesystem-safe slug from region type and name.

    Examples:
        National, "United States" -> "national-united_states"
        State, "California"      -> "state-california"
        State, "New York"        -> "state-new_york"
        Metro, "Atlanta-Sandy Springs-Alpharetta, GA" -> "metro-atlanta"
        Metro, "St. Louis, MO-IL" -> "metro-st_louis"
        Metro, "Minneapolis-St. Paul-Bloomington, MN-WI" -> "metro-minneapolis"
    """
    prefix = region_type.lower()

    if region_type == "Metro":
        # Take first city only (before first '-' or ',')
        city = re.split(r"[-,]", region_name)[0].strip()
    else:
        city = region_name

    # Lowercase, spaces to underscores, strip non-alphanumeric (keep underscores)
    slug_part = city.lower().replace(" ", "_").replace(".", "")
    slug_part = re.sub(r"[^a-z0-9_]", "", slug_part)

    return f"{prefix}-{slug_part}"


def _query_all(conn: sqlite3.Connection,
               country_codes: list[str] | None = None) -> list[dict]:
    """Query all occupation records with country code."""
    query = """
        SELECT o.year, r.region_type, r.name as region,
               o.occupation_code, o.occupation_title, o.major_group_name,
               o.employment, o.mean_annual_wage, o.gdp, o.complexity_score,
               c.code as country_code
        FROM occupations o
        JOIN regions r ON o.region_id = r.id
        JOIN countries c ON r.country_id = c.id
    """
    params: list = []
    if country_codes:
        placeholders = ",".join("?" * len(country_codes))
        query += f" WHERE c.code IN ({placeholders})"
        params = list(country_codes)
    query += " ORDER BY r.region_type, r.name, o.occupation_code"

    rows = []
    for row in conn.execute(query, params).fetchall():
        (year, region_type, region, occ_code, occ_title, major_group,
         employment, wage, gdp, complexity, country_code) = row
        rows.append({
            "year": year,
            "region_type": region_type,
            "region": region,
            "occ_code": occ_code,
            "occ_title": occ_title,
            "major_group": major_group,
            "employment": employment,
            "wage": wage,
            "gdp": gdp,
            "complexity": round(complexity, 4),
            "country_code": country_code,
        })
    return rows


def _country_code_to_short(code: str) -> str:
    """Convert 3-letter country code to short form for filenames.

    USA -> us, GBR -> gb, IND -> in, etc.
    """
    mapping = {
        "USA": "us", "GBR": "gb", "IND": "in", "EGY": "eg",
        "CAN": "ca", "MEX": "mx", "EUU": "eu",
    }
    return mapping.get(code, code.lower()[:2])


def export_split(conn: sqlite3.Connection,
                 country_codes: list[str] | None = None,
                 output_dir: Path | None = None) -> dict:
    """Generate meta.js + per-region data files.

    Returns dict with stats: {meta_path, region_count, occ_count, files}.
    """
    if output_dir is None:
        output_dir = config.DATA_DIR

    records = _query_all(conn, country_codes)

    # Build occupation lookup (deduplicate, preserve order)
    occ_seen: dict[str, int] = {}
    occ_list: list[list] = []  # [soc_code, title, major_group_prefix, major_group_name]
    for r in records:
        if r["occ_code"] not in occ_seen:
            prefix = r["occ_code"][:2] if "-" in r["occ_code"] else ""
            occ_seen[r["occ_code"]] = len(occ_list)
            occ_list.append([
                r["occ_code"], r["occ_title"], prefix, r["major_group"]
            ])

    # Group records by (year, region_type, region, country_code)
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        key = (r["year"], r["region_type"], r["region"], r["country_code"])
        groups.setdefault(key, []).append(r)

    # Build region manifest and write region files
    years_set: set[int] = set()
    regions_by_type: dict[str, list[list]] = {}  # type -> [[slug, display, country_short]]
    region_dir = output_dir / "regions"
    region_dir.mkdir(parents=True, exist_ok=True)

    files_written = []

    for (year, region_type, region_name, country_code), group_records in groups.items():
        years_set.add(year)
        slug = _make_slug(region_type, region_name)
        country_short = _country_code_to_short(country_code)

        # Add to manifest (deduplicate by slug)
        if region_type not in regions_by_type:
            regions_by_type[region_type] = []
        entry = [slug, region_name, country_short]
        if entry not in regions_by_type[region_type]:
            regions_by_type[region_type].append(entry)

        # Build compact rows: [occ_index, employment, wage, gdp, complexity_score]
        compact_rows = []
        for r in group_records:
            occ_idx = occ_seen[r["occ_code"]]
            compact_rows.append([
                occ_idx, r["employment"], r["wage"], r["gdp"], r["complexity"]
            ])

        # Write region file
        filename = f"{year}.{slug}.{country_short}.data.js"
        filepath = region_dir / filename
        rows_json = json.dumps(compact_rows)
        filepath.write_text(
            f"window.BLS_LOAD({rows_json});\n",
            encoding="utf-8",
        )
        files_written.append(filename)

    # Sort regions within each type
    for rt in regions_by_type:
        regions_by_type[rt].sort(key=lambda x: x[1])

    # Write meta.js
    meta = {
        "years": sorted(years_set),
        "occ": occ_list,
        "regions": regions_by_type,
    }
    meta_json = json.dumps(meta, indent=2)
    meta_path = output_dir / "meta.js"
    meta_path.write_text(
        f"window.BLS_META = {meta_json};\n",
        encoding="utf-8",
    )

    return {
        "meta_path": str(meta_path),
        "region_count": len(files_written),
        "occ_count": len(occ_list),
        "files": files_written,
    }
