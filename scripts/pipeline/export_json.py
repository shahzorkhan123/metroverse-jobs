"""Generate frontend JSON files from SQLite.

Country-tagged output structure:
  - public/data/bls-data.json              (meta catalog)
  - public/data/bls-data-us-2024.json      (levels 1+2, main data)
  - public/data/bls-data-us-2024-3.json    (level 3 extension — broad)
  - public/data/bls-data-us-2024-4.json    (level 4 extension — detailed, nat+state)
  - public/data/bls-data-us-2024-4-metro.json (level 4 extension — detailed, metro)
"""

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

from . import config

SOC_MAJOR_GROUP_COLORS = config.SOC_MAJOR_GROUP_COLORS
NCO_MAJOR_GROUP_COLORS = config.NCO_MAJOR_GROUP_COLORS


def _soc_level(soc_code: str) -> int:
    """BLS SOC hierarchy: 4 real levels.

    XX-0000 = 1 (major group)
    XX-X000 = 2 (minor group)
    XX-XX00 = 2 (minor group — SOC 2018 renumbered codes)
    XX-XXX0 = 3 (broad occupation)
    XX-XXXX = 4 (detailed occupation)
    """
    if soc_code.endswith("-0000"):
        return 1
    elif soc_code.endswith("00"):  # catches both XX-X000 and XX-XX00
        return 2
    elif soc_code.endswith("0"):
        return 3
    else:
        return 4


def _soc_parent(soc_code: str, known_codes: set[str] | None = None) -> str | None:
    """Get parent SOC code for hierarchy traversal.

    For level 3 (XX-XXX0), the parent minor group can be either
    XX-X000 (standard) or XX-XX00 (SOC 2018 renumbered).  When
    *known_codes* is provided we check which pattern actually exists;
    otherwise we default to the standard XX-X000 pattern.
    """
    level = _soc_level(soc_code)
    prefix = soc_code[:3]  # "XX-"
    if level == 4:
        return prefix + soc_code[3:6] + "0"   # XX-XXXX → XX-XXX0
    if level == 3:
        renumbered = prefix + soc_code[3:5] + "00"   # XX-XX00
        standard   = prefix + soc_code[3] + "000"    # XX-X000
        if renumbered == standard:
            return standard
        if known_codes is not None:
            return renumbered if renumbered in known_codes else standard
        return standard  # safe default
    if level == 2:
        return prefix + "0000"                  # XX-X000 → XX-0000
    return None  # level 1 has no parent


def _nco_level(nco_code: str) -> int:
    """NCO hierarchy: level = number of digits in the code."""
    return len(nco_code.strip())


def _nco_parent(nco_code: str, known_codes: set[str] | None = None) -> str | None:
    """Get parent NCO code: drop last digit."""
    code = nco_code.strip()
    if len(code) <= 1:
        return None
    return code[:-1]


def _nco_major_group_id(nco_code: str) -> str:
    """Get the 1-digit division (major group) for any NCO code."""
    return nco_code[0]


def _get_level(occ_code: str, code_system: str) -> int:
    """Dispatch to SOC or NCO level function."""
    if code_system == "NCO":
        return _nco_level(occ_code)
    return _soc_level(occ_code)


def _get_parent(occ_code: str, code_system: str,
                known_codes: set[str] | None = None) -> str | None:
    """Dispatch to SOC or NCO parent function."""
    if code_system == "NCO":
        return _nco_parent(occ_code, known_codes)
    return _soc_parent(occ_code, known_codes)


def _get_major_group_id(occ_code: str, code_system: str) -> str:
    """Get the major group ID for an occupation code."""
    if code_system == "NCO":
        return _nco_major_group_id(occ_code)
    # SOC: first two digits (e.g. "11" from "11-1011")
    return occ_code[:2] if "-" in occ_code else occ_code[:1]


def _get_major_group_colors(code_system: str) -> dict[str, str]:
    """Get the color map for a code system."""
    if code_system == "NCO":
        return NCO_MAJOR_GROUP_COLORS
    return SOC_MAJOR_GROUP_COLORS


def _synthesize_missing_levels(records: list[dict],
                               code_system: str = "SOC") -> list[dict]:
    """Synthesize missing intermediate SOC levels by aggregating children.

    BLS doesn't publish level 2 (minor group) or some level 3 (broad) data
    for states and metros.  This creates synthetic records by summing
    immediate children, processed bottom-up (level 3 from level 4, then
    level 2 from level 3).

    Occupation names are looked up from other regions (national usually has
    every code).
    """
    from collections import defaultdict

    # Build global name + major-group-name lookup
    soc_names: dict[str, str] = {}
    soc_mg_names: dict[str, str] = {}
    for r in records:
        code = r["SOC_Code"]
        if code not in soc_names:
            soc_names[code] = r["OCC_TITLE"]
        mg = _get_major_group_id(code, code_system)
        if mg not in soc_mg_names:
            soc_mg_names[mg] = r.get("SOC_Major_Group_Name", "")

    # Build global set of all codes (national data has the complete hierarchy)
    all_codes = {r["SOC_Code"] for r in records}

    # Group records by (region_type, region, year)
    by_region_year: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in records:
        key = (r["Region_Type"], r["Region"], r["year"])
        by_region_year[key][r["SOC_Code"]] = r

    all_synthetic: list[dict] = []

    # Determine max level for synthesis based on code system
    max_level = 4 if code_system == "SOC" else 3

    for (rt, region, year), code_map in by_region_year.items():
        # Bottom-up: synthesize from highest level down to level 2
        for target_level in range(max_level - 1, 1, -1):
            child_level = target_level + 1
            missing_parents: dict[str, list[dict]] = defaultdict(list)

            for code, rec in list(code_map.items()):
                if _get_level(code, code_system) == child_level:
                    parent = _get_parent(code, code_system, all_codes)
                    if (parent
                            and _get_level(parent, code_system) == target_level
                            and parent not in code_map):
                        missing_parents[parent].append(rec)

            for parent_code, children in missing_parents.items():
                total_emp = sum(c["TOT_EMP"] for c in children)
                total_gdp = sum(c["GDP"] for c in children)
                a_mean = round(total_gdp / total_emp) if total_emp > 0 else 0
                major_group = _get_major_group_id(parent_code, code_system)

                if total_emp > 0:
                    complexity = sum(
                        c.get("complexity_score", 0.5) * c["TOT_EMP"]
                        for c in children
                    ) / total_emp
                else:
                    complexity = 0.5

                fallback_prefix = "NCO" if code_system == "NCO" else "SOC"
                synth = {
                    "year": year,
                    "Region_Type": rt,
                    "Region": region,
                    "SOC_Code": parent_code,
                    "OCC_TITLE": soc_names.get(parent_code, f"{fallback_prefix} {parent_code}"),
                    "SOC_Major_Group": major_group,
                    "SOC_Major_Group_Name": soc_mg_names.get(major_group, ""),
                    "TOT_EMP": total_emp,
                    "A_MEAN": a_mean,
                    "GDP": total_gdp,
                    "complexity_score": round(complexity, 4),
                }

                # Add to code_map so level 2 synthesis can use synthesized level 3
                code_map[parent_code] = synth
                all_synthetic.append(synth)

    return all_synthetic


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
               o.employment, o.mean_annual_wage, o.gdp, o.complexity_score,
               c.code_system
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
         employment, wage, gdp, complexity, code_system) = row
        # SOC uses XX-XXXX format with dash; NCO uses plain digits
        if "-" in occ_code:
            soc_group = occ_code[:2]
        else:
            soc_group = occ_code[0]  # NCO: 1-digit division
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


def _detect_code_system(conn: sqlite3.Connection,
                        country_code: str) -> str:
    """Look up code_system from the countries table."""
    row = conn.execute(
        "SELECT code_system FROM countries WHERE code = ?",
        (country_code,),
    ).fetchone()
    return row[0] if row else "SOC"


def _build_static_data(records: list[dict],
                       max_level: int | None = None,
                       exact_level: int | None = None,
                       code_system: str = "SOC",
                       slim_occupations: bool = False) -> dict:
    """Build the static data structure for a BLS JSON file.

    If max_level is set, only include occupations at levels <= max_level.
    If exact_level is set, only include occupations at exactly that level.
    """
    # Synthesize missing intermediate levels before filtering.
    synthetic = _synthesize_missing_levels(records, code_system)
    if synthetic:
        records = records + synthetic

    if exact_level is not None:
        filtered = [r for r in records
                    if _get_level(r["SOC_Code"], code_system) == exact_level]
    elif max_level is not None:
        filtered = [r for r in records
                    if _get_level(r["SOC_Code"], code_system) <= max_level]
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
    all_soc_codes = set(occupations_set.keys())
    color_map = _get_major_group_colors(code_system)
    occupations = []
    occupation_map: dict[str, dict] = {}
    for soc_code in sorted(occupations_set.keys()):
        occ = occupations_set[soc_code]
        occ_record = {
            "socCode": soc_code,
            "name": occ["name"],
            "level": _get_level(soc_code, code_system),
            "parentCode": _get_parent(soc_code, code_system, all_soc_codes),
            "majorGroupId": occ["majorGroupId"],
            "majorGroupName": occ["majorGroupName"],
        }
        occupation_map[soc_code] = {
            "name": occ_record["name"],
            "level": occ_record["level"],
            "parentCode": occ_record["parentCode"],
            "majorGroupId": occ_record["majorGroupId"],
            "majorGroupName": occ_record["majorGroupName"],
        }
        if not slim_occupations:
            occupations.append(occ_record)

    # Build major groups array
    major_groups = []
    for gid in sorted(major_groups_set.keys()):
        color = color_map.get(gid, "#999999")
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

    # Source attribution based on code system
    if code_system == "NCO":
        source = "PLFS Annual Report 2023-24, Tables 25 and 50"
    else:
        source = "BLS OES + O*NET"

    metadata = {
        "lastUpdated": date.today().isoformat(),
        "years": sorted(years),
        "source": source,
    }
    if slim_occupations:
        metadata["occupationMap"] = occupation_map

    output = {
        "metadata": metadata,
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

    code_system = _detect_code_system(conn, country_code)
    records = _query_records(conn, [country_code])
    # Filter to requested year
    records = [r for r in records if r["year"] == year]
    data = _build_static_data(records, max_level=2, code_system=code_system)
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
                      output_path: Path | None = None,
                      region_types: list[str] | None = None) -> int:
    """Generate a level extension JSON file (single level only).

    If region_types is set, only include those region types (e.g. ["National", "State"]).
    Returns record count for this level.
    """
    short = config.country_short(country_code)
    if output_path is None:
        output_path = config.json_country_year_level_path(short, year, level)

    code_system = _detect_code_system(conn, country_code)
    records = _query_records(conn, [country_code])
    records = [r for r in records if r["year"] == year]
    if region_types:
        records = [r for r in records if r["Region_Type"] in region_types]
    data = _build_static_data(
        records,
        exact_level=level,
        code_system=code_system,
        slim_occupations=(country_code == "IND"),
    )
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
        year (int), levels_available (list[int]),
        level_files_extra (dict[str,str], optional) — extra level file keys
    """
    if output_path is None:
        output_path = config.json_meta_path()

    # Start from existing meta if present, so exporting one country doesn't drop others.
    existing = {}
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    datasets_by_key: dict[tuple[str, int], dict] = {}
    for item in existing.get("datasets", []):
        datasets_by_key[(item.get("country"), item.get("year"))] = item

    level_files: dict[str, dict[str, str]] = {
        k: dict(v) for k, v in existing.get("levelFiles", {}).items()
    }
    countries_map: dict[str, dict] = {
        c.get("code"): dict(c)
        for c in existing.get("countries", [])
        if c.get("code")
    }
    years_by_country: dict[str, set[int]] = {
        c: set(int(y) for y in ys)
        for c, ys in existing.get("yearsByCountry", {}).items()
    }
    country_metadata = dict(existing.get("countryMetadata", {}))

    code_to_flag = {
        "us": "US",
        "in": "IN",
        "gb": "GB",
        "eg": "EG",
        "ca": "CA",
        "mx": "MX",
        "eu": "EU",
    }

    # reverse map short -> long country code
    short_to_long = {
        config.country_short(long_code): long_code
        for long_code in config.COUNTRIES
    }

    def default_country_metadata(long_code: str) -> dict:
        cfg = config.COUNTRIES.get(long_code, {})
        code_system = cfg.get("code_system", "SOC")
        currency = cfg.get("currency", "USD")

        if code_system == "NCO":
            major_groups = [
                {
                    "id": gid,
                    "name": config.NCO_MAJOR_GROUPS.get(gid, f"Division {gid}"),
                    "color": config.NCO_MAJOR_GROUP_COLORS.get(gid, "#999999"),
                }
                for gid in sorted(config.NCO_MAJOR_GROUP_COLORS.keys())
            ]
            return {
                "classificationSystem": "NCO",
                "currency": currency,
                "currencySymbol": "₹" if currency == "INR" else currency,
                "terminology": {
                    "occupationCode": "NCO Code",
                    "majorGroup": "Division",
                    "wage": "Annual Mean Wage",
                    "employment": "Workers",
                },
                "levels": {
                    "1": {"name": "Division"},
                    "2": {"name": "Sub-Division"},
                    "3": {"name": "Group"},
                },
                "maxLevel": 3,
                "regionTypes": [
                    {"id": "National", "pluralName": "National"},
                    {"id": "State", "pluralName": "States/UTs"},
                    {"id": "Metro", "pluralName": "Cities"},
                ],
                "majorGroups": major_groups,
                "hierarchyRules": {"strategy": "nco2015"},
            }

        major_groups = [
            {
                "id": gid,
                "name": config.SOC_MAJOR_GROUPS.get(gid, gid),
                "color": config.SOC_MAJOR_GROUP_COLORS.get(gid, "#999999"),
            }
            for gid in sorted(config.SOC_MAJOR_GROUP_COLORS.keys())
        ]
        return {
            "classificationSystem": "SOC",
            "currency": currency,
            "currencySymbol": "$" if currency == "USD" else currency,
            "terminology": {
                "occupationCode": "SOC Code",
                "majorGroup": "Major Group",
                "wage": "Annual Mean Wage",
                "employment": "Employment",
            },
            "levels": {
                "1": {"name": "Major Group"},
                "2": {"name": "Minor Group"},
                "3": {"name": "Broad Occupation"},
                "4": {"name": "Detailed Occupation"},
            },
            "maxLevel": 4,
            "regionTypes": [
                {"id": "National", "pluralName": "National"},
                {"id": "State", "pluralName": "States"},
                {"id": "Metro", "pluralName": "Metropolitan Areas"},
            ],
            "majorGroups": major_groups,
            "hierarchyRules": {"strategy": "soc2018"},
        }

    for cfg in country_configs:
        short = cfg["country_short"]
        year = cfg["year"]
        name = cfg["country_name"]
        levels = cfg["levels_available"]

        datasets_by_key[(short, year)] = {
            "country": short,
            "year": year,
            "file": f"bls-data-{short}-{year}.json",
            "levels": [1, 2],
        }

        key = f"{short}-{year}"
        if key not in level_files:
            level_files[key] = {}
        for lvl in levels:
            if lvl > 2:
                level_files[key][str(lvl)] = f"bls-data-{short}-{year}-{lvl}.json"
        for lkey, lfile in cfg.get("level_files_extra", {}).items():
            level_files[key][lkey] = lfile

        country_entry = {
            "code": short,
            "name": name,
        }
        existing_country_entry = countries_map.get(short, {})
        if "flagEmoji" in existing_country_entry:
            country_entry["flagEmoji"] = existing_country_entry["flagEmoji"]
        countries_map[short] = country_entry

        years_by_country.setdefault(short, set()).add(year)

        long_code = cfg.get("country_code") or short_to_long.get(short)
        if long_code:
            country_metadata[short] = default_country_metadata(long_code)

    years_seen = sorted({d["year"] for d in datasets_by_key.values()})
    datasets = sorted(
        datasets_by_key.values(),
        key=lambda d: (d["country"], d["year"]),
    )

    meta = {
        "datasets": datasets,
        "levelFiles": level_files,
        "countries": [countries_map[c] for c in sorted(countries_map.keys())],
        "years": years_seen,
        "yearsByCountry": {
            c: sorted(list(ys)) for c, ys in sorted(years_by_country.items())
        },
        "countryMetadata": country_metadata,
        "lastUpdated": date.today().isoformat(),
    }

    _write_json(meta, output_path)
    print(f"  {output_path.name}: {len(datasets)} datasets, "
            f"{len(countries_map)} countries")


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
    code_system = _detect_code_system(conn, country_code)
    records = _query_records(conn, [country_code])
    records = [r for r in records if r["year"] == year]
    all_levels = sorted(set(_get_level(r["SOC_Code"], code_system) for r in records))

    # Export level extension files
    level_counts: dict[int, int] = {}
    level_files_extra: dict[str, str] = {}
    for level in all_levels:
        if level > 2:
            if level >= 3:
                # Split level 3 and 4: nat+state vs metro
                count_ns = export_level_file(
                    conn, country_code, year, level,
                    region_types=["National", "State"],
                )
                metro_path = config.json_country_year_level_path(short, year, f"{level}-metro")
                count_metro = export_level_file(
                    conn, country_code, year, level,
                    output_path=metro_path,
                    region_types=["Metro"],
                )
                total_count = count_ns + count_metro
                if total_count > 0:
                    level_counts[level] = total_count
                if count_metro > 0:
                    level_files_extra[f"{level}-metro"] = f"bls-data-{short}-{year}-{level}-metro.json"
            else:
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
        "level_files_extra": level_files_extra,
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
