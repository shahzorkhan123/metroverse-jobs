"""Generate frontend JSON files from SQLite.

Country-tagged output structure:
  - public/data/bls-data.json              (meta catalog)
  - public/data/bls-data-us-2024.json      (levels 1+2, main data)
  - public/data/bls-data-us-2024-3.json    (level 3 extension)
  - public/data/bls-data-us-2024-4.json    (level 4 extension)
  - public/data/bls-data-us-2024-5.json    (level 5 extension)
"""

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

from . import config

SOC_MAJOR_GROUP_COLORS = config.SOC_MAJOR_GROUP_COLORS


def _soc_level(soc_code: str) -> int:
    """Determine the SOC digit level for a code.

    XX-0000 = level 1 (major group)
    XX-X000 = level 2 (minor group)
    XX-XX00 = level 3 (broad occupation)
    XX-XXX0 = level 4 (detailed)
    XX-XXXX = level 5 (most detailed)
    """
    if soc_code.endswith("-0000"):
        return 1
    elif soc_code.endswith("000"):
        return 2
    elif soc_code.endswith("00"):
        return 3
    elif soc_code.endswith("0"):
        return 4
    else:
        return 5


def _make_region_id(region_type: str, region_name: str) -> str:
    """Create a URL-safe region ID from type and name."""
    slug = re.sub(r"[^a-z0-9]+", "-", region_name.lower()).strip("-")
    return f"{region_type.lower()}-{slug}"


def _query_records(conn: sqlite3.Connection,
                   country_codes: list[str] | None = None) -> list[dict]:
    """Query all occupation records from SQLite."""
    query = """
        SELECT o.year, r.region_type, r.name as region,
               o.occupation_code, o.occupation_title, o.major_group_name,
               o.employment, o.mean_annual_wage, o.gdp, o.complexity_score
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

    records = []
    for row in conn.execute(query, params).fetchall():
        (year, region_type, region, occ_code, occ_title, major_group,
         employment, wage, gdp, complexity) = row
        soc_group = occ_code[:2] if "-" in occ_code else ""
        records.append({
            "year": year,
            "Region_Type": region_type,
            "Region": region,
            "SOC_Code": occ_code,
            "OCC_TITLE": occ_title,
            "SOC_Major_Group": soc_group,
            "SOC_Major_Group_Name": major_group,
            "TOT_EMP": employment,
            "A_MEAN": wage,
            "GDP": gdp,
            "complexity_score": round(complexity, 4),
        })
    return records


def _build_static_data(records: list[dict],
                       max_level: int | None = None,
                       exact_level: int | None = None) -> dict:
    """Build the static data structure for a BLS JSON file.

    If max_level is set, only include occupations at levels <= max_level.
    If exact_level is set, only include occupations at exactly that level.
    """
    if exact_level is not None:
        filtered = [r for r in records
                    if _soc_level(r["SOC_Code"]) == exact_level]
    elif max_level is not None:
        filtered = [r for r in records
                    if _soc_level(r["SOC_Code"]) <= max_level]
    else:
        filtered = records

    # Collect unique values
    regions_set: dict[tuple, str] = {}
    occupations_set: dict[str, dict] = {}
    major_groups_set: dict[str, str] = {}
    years: set[int] = set()

    for record in filtered:
        rt = record["Region_Type"]
        rn = record["Region"]
        key = (rt, rn)
        if key not in regions_set:
            regions_set[key] = _make_region_id(rt, rn)

        soc = record["SOC_Code"]
        if soc not in occupations_set:
            occupations_set[soc] = {
                "name": record["OCC_TITLE"],
                "majorGroupId": record["SOC_Major_Group"],
                "majorGroupName": record["SOC_Major_Group_Name"],
            }

        mg = record["SOC_Major_Group"]
        if mg and mg not in major_groups_set:
            major_groups_set[mg] = record["SOC_Major_Group_Name"]

        years.add(record["year"])

    # Build regions array
    regions = []
    for (rt, rn), rid in sorted(regions_set.items(), key=lambda x: (x[0][0], x[0][1])):
        regions.append({
            "regionId": rid,
            "name": rn,
            "regionType": rt,
        })

    # Build occupations array
    occupations = []
    for soc_code in sorted(occupations_set.keys()):
        occ = occupations_set[soc_code]
        occupations.append({
            "socCode": soc_code,
            "name": occ["name"],
            "level": _soc_level(soc_code),
            "majorGroupId": occ["majorGroupId"],
            "majorGroupName": occ["majorGroupName"],
        })

    # Build major groups array
    major_groups = []
    for gid in sorted(major_groups_set.keys()):
        color = SOC_MAJOR_GROUP_COLORS.get(gid, "#999999")
        major_groups.append({
            "groupId": gid,
            "name": major_groups_set[gid],
            "color": color,
        })

    # Build regionData
    region_data: dict[str, dict[str, list]] = {}
    for record in filtered:
        rid = regions_set[(record["Region_Type"], record["Region"])]
        year_str = str(record["year"])

        if rid not in region_data:
            region_data[rid] = {}
        if year_str not in region_data[rid]:
            region_data[rid][year_str] = []

        region_data[rid][year_str].append({
            "socCode": record["SOC_Code"],
            "totEmp": record["TOT_EMP"],
            "gdp": record["GDP"],
            "aMean": record["A_MEAN"],
            "complexity": record.get("complexity_score", 0.5),
        })

    # Build aggregates
    aggregates: dict[str, dict] = {}
    for year in sorted(years):
        year_str = str(year)
        year_records = [r for r in filtered if r["year"] == year]

        occ_data: dict[str, dict] = {}
        all_wages: list[int] = []
        all_complexity: list[float] = []

        for r in year_records:
            soc = r["SOC_Code"]
            if soc not in occ_data:
                occ_data[soc] = {"totalEmploy": 0, "totalGdp": 0,
                                 "wages": [], "complexities": []}
            occ_data[soc]["totalEmploy"] += r["TOT_EMP"]
            occ_data[soc]["totalGdp"] += r["GDP"]
            occ_data[soc]["wages"].append(r["A_MEAN"])
            occ_data[soc]["complexities"].append(r.get("complexity_score", 0.5))
            all_wages.append(r["A_MEAN"])
            all_complexity.append(r.get("complexity_score", 0.5))

        by_occupation = {}
        for soc, d in occ_data.items():
            by_occupation[soc] = {
                "totalEmploy": d["totalEmploy"],
                "avgWage": (sum(d["wages"]) / len(d["wages"])
                            if d["wages"] else 0),
                "avgComplexity": (sum(d["complexities"]) / len(d["complexities"])
                                  if d["complexities"] else 0),
            }

        all_wages_sorted = sorted(all_wages)
        all_complexity_sorted = sorted(all_complexity)
        mid = len(all_wages_sorted) // 2

        aggregates[year_str] = {
            "byOccupation": by_occupation,
            "minMaxStats": {
                "minWage": min(all_wages) if all_wages else 0,
                "maxWage": max(all_wages) if all_wages else 0,
                "medianWage": all_wages_sorted[mid] if all_wages_sorted else 0,
                "minComplexity": min(all_complexity) if all_complexity else 0,
                "maxComplexity": max(all_complexity) if all_complexity else 1,
                "medianComplexity": (all_complexity_sorted[mid]
                                     if all_complexity_sorted else 0.5),
            },
        }

    output = {
        "metadata": {
            "lastUpdated": date.today().isoformat(),
            "years": sorted(years),
            "source": "BLS OES + O*NET",
        },
        "regions": regions,
        "occupations": occupations,
        "majorGroups": major_groups,
        "regionData": region_data,
        "aggregates": aggregates,
    }

    if max_level is not None:
        output["metadata"]["maxLevel"] = max_level
    if exact_level is not None:
        output["metadata"]["level"] = exact_level

    return output


def _write_json(data: dict, path: Path) -> int:
    """Write data as JSON and return file size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path.stat().st_size


def export_country_year(conn: sqlite3.Connection,
                        country_code: str,
                        year: int,
                        output_path: Path | None = None) -> int:
    """Generate the main country-year JSON file (levels 1+2).

    Returns record count.
    """
    short = config.country_short(country_code)
    if output_path is None:
        output_path = config.json_country_year_path(short, year)

    records = _query_records(conn, [country_code])
    # Filter to requested year
    records = [r for r in records if r["year"] == year]
    data = _build_static_data(records, max_level=2)
    data["metadata"]["country"] = short
    data["metadata"]["maxLevel"] = 2

    file_size = _write_json(data, output_path)
    record_count = sum(
        len(entries)
        for year_data in data["regionData"].values()
        for entries in year_data.values()
    )
    print(f"  {output_path.name}: {len(data['occupations'])} occupations, "
          f"{record_count} region-records ({file_size:,} bytes)")
    return record_count


def export_level_file(conn: sqlite3.Connection,
                      country_code: str,
                      year: int,
                      level: int,
                      output_path: Path | None = None) -> int:
    """Generate a level extension JSON file (single level only).

    Returns record count for this level.
    """
    short = config.country_short(country_code)
    if output_path is None:
        output_path = config.json_country_year_level_path(short, year, level)

    records = _query_records(conn, [country_code])
    records = [r for r in records if r["year"] == year]
    data = _build_static_data(records, exact_level=level)
    data["metadata"]["country"] = short
    data["metadata"]["level"] = level

    record_count = sum(
        len(entries)
        for year_data in data["regionData"].values()
        for entries in year_data.values()
    )

    # Only write if there are records at this level
    if record_count > 0:
        file_size = _write_json(data, output_path)
        print(f"  {output_path.name}: {len(data['occupations'])} occupations, "
              f"{record_count} region-records ({file_size:,} bytes)")
    return record_count


def export_meta(country_configs: list[dict],
                output_path: Path | None = None) -> None:
    """Generate the meta catalog file (bls-data.json).

    country_configs: list of dicts with keys:
        country_code (str), country_short (str), country_name (str),
        year (int), levels_available (list[int])
    """
    if output_path is None:
        output_path = config.json_meta_path()

    datasets = []
    level_files: dict[str, dict[str, str]] = {}
    countries_seen: dict[str, str] = {}
    years_seen: set[int] = set()

    for cfg in country_configs:
        short = cfg["country_short"]
        year = cfg["year"]
        name = cfg["country_name"]
        levels = cfg["levels_available"]

        countries_seen[short] = name
        years_seen.add(year)

        main_file = f"bls-data-{short}-{year}.json"
        datasets.append({
            "country": short,
            "year": year,
            "file": main_file,
            "levels": [1, 2],
        })

        key = f"{short}-{year}"
        level_files[key] = {}
        for lvl in levels:
            if lvl > 2:
                level_files[key][str(lvl)] = f"bls-data-{short}-{year}-{lvl}.json"

    meta = {
        "datasets": datasets,
        "levelFiles": level_files,
        "countries": [{"code": c, "name": n}
                      for c, n in sorted(countries_seen.items())],
        "years": sorted(years_seen),
        "lastUpdated": date.today().isoformat(),
    }

    _write_json(meta, output_path)
    print(f"  {output_path.name}: {len(datasets)} datasets, "
          f"{len(countries_seen)} countries")


def export_all(conn: sqlite3.Connection,
               country_code: str = "USA",
               year: int = 2024) -> dict:
    """Export all JSON files for a country-year.

    Returns dict with stats.
    """
    short = config.country_short(country_code)
    country_name = config.COUNTRIES.get(country_code, {}).get("name", country_code)

    # Export main file (levels 1+2)
    main_count = export_country_year(conn, country_code, year)

    # Determine which levels exist in data
    records = _query_records(conn, [country_code])
    records = [r for r in records if r["year"] == year]
    all_levels = sorted(set(_soc_level(r["SOC_Code"]) for r in records))

    # Export level extension files (3, 4, 5)
    level_counts: dict[int, int] = {}
    for level in all_levels:
        if level > 2:
            count = export_level_file(conn, country_code, year, level)
            if count > 0:
                level_counts[level] = count

    # Export meta catalog
    levels_available = [lvl for lvl in all_levels if lvl > 2 and lvl in level_counts]
    export_meta([{
        "country_code": country_code,
        "country_short": short,
        "country_name": country_name,
        "year": year,
        "levels_available": levels_available,
    }])

    return {
        "main_count": main_count,
        "level_counts": level_counts,
        "levels_available": all_levels,
    }


# --- Legacy API (kept for backward compatibility with existing tests) ---

def export_json(conn: sqlite3.Connection,
                country_codes: list[str] | None = None,
                output_path: Path | None = None) -> int:
    """Generate a full bls-data.json with all levels. Returns record count.

    This is the legacy single-file export. For the new country-tagged
    format, use export_all() instead.
    """
    if output_path is None:
        output_path = config.JSON_FULL_PATH

    records = _query_records(conn, country_codes)
    data = _build_static_data(records)

    file_size = _write_json(data, output_path)
    print(f"  {output_path.name}: {len(records)} records ({file_size:,} bytes)")
    return len(records)


def export_json_levels(conn: sqlite3.Connection,
                       country_codes: list[str] | None = None,
                       max_levels: list[int] | None = None) -> dict[int, int]:
    """Generate per-level split JSON files (legacy cumulative format).

    Returns dict of level -> record count.
    """
    records = _query_records(conn, country_codes)
    all_levels = sorted(set(_soc_level(r["SOC_Code"]) for r in records))

    if max_levels is None:
        max_levels = all_levels

    results: dict[int, int] = {}
    for level in max_levels:
        if level not in all_levels and level > max(all_levels):
            continue

        data = _build_static_data(records, max_level=level)
        output_path = config.json_level_path(level)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        level_records = sum(
            len(entries)
            for year_data in data["regionData"].values()
            for entries in year_data.values()
        )
        file_size = output_path.stat().st_size
        print(f"  {output_path.name}: {len(data['occupations'])} occupations, "
              f"{level_records} region-records ({file_size:,} bytes)")
        results[level] = level_records

    return results
