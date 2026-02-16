#!/usr/bin/env python3
"""
Generate static BLS data JSON for metroverse-jobs.

Reads BLS data from ../bls2/data/job_data.js (JSONP format)
and outputs public/data/bls-data.json.

Usage:
    python scripts/generate-static-data.py
    python scripts/generate-static-data.py --input ../bls2/data/job_data.js
"""

import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

# SOC Major Group colors (22 groups, distinct colors)
SOC_MAJOR_GROUP_COLORS = {
    "11": "#A973BE",  # Management - Purple
    "13": "#F1866C",  # Business and Financial - Coral
    "15": "#488098",  # Computer and Mathematical - Steel Blue
    "17": "#6A6AAD",  # Architecture and Engineering - Indigo
    "19": "#77C898",  # Life, Physical, Social Science - Green
    "21": "#93CFD0",  # Community and Social Service - Teal
    "23": "#D35162",  # Legal - Crimson
    "25": "#FFC135",  # Educational Instruction - Gold
    "27": "#F28188",  # Arts, Design, Entertainment - Pink
    "29": "#5B9BD5",  # Healthcare Practitioners - Blue
    "31": "#70AD47",  # Healthcare Support - Lime Green
    "33": "#BF8F00",  # Protective Service - Dark Gold
    "35": "#ED7D31",  # Food Preparation - Orange
    "37": "#8DB4E2",  # Building and Grounds - Light Blue
    "39": "#C5B0D5",  # Personal Care - Lavender
    "41": "#FF6B6B",  # Sales - Red
    "43": "#4ECDC4",  # Office and Administrative - Cyan
    "45": "#556B2F",  # Farming, Fishing, Forestry - Olive
    "47": "#DAA520",  # Construction - Goldenrod
    "49": "#708090",  # Installation, Maintenance - Slate Gray
    "51": "#CD853F",  # Production - Peru
    "53": "#9370DB",  # Transportation - Medium Purple
}


def parse_jsonp_file(filepath: str) -> list:
    """Parse the JSONP-style job_data.js file and extract the jobData array."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the jobData array
    start_marker = "jobData: ["
    start_idx = content.index(start_marker) + len("jobData: ")

    # Find matching bracket
    depth = 0
    end_idx = start_idx
    for i, c in enumerate(content[start_idx:], start_idx):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        if depth == 0:
            end_idx = i + 1
            break

    return json.loads(content[start_idx:end_idx])


def make_region_id(region_type: str, region_name: str) -> str:
    """Create a URL-safe region ID from type and name."""
    slug = re.sub(r"[^a-z0-9]+", "-", region_name.lower()).strip("-")
    return f"{region_type.lower()}-{slug}"


def generate_static_data(input_path: str, output_path: str):
    """Generate the static BLS data JSON file."""
    print(f"Reading data from: {input_path}")
    raw_data = parse_jsonp_file(input_path)
    print(f"Parsed {len(raw_data)} records")

    # Collect unique values
    regions_set = {}  # (type, name) -> regionId
    occupations_set = {}  # socCode -> {name, majorGroup, majorGroupName}
    major_groups_set = {}  # groupId -> name
    years = set()

    for record in raw_data:
        rt = record["Region_Type"]
        rn = record["Region"]
        key = (rt, rn)
        if key not in regions_set:
            regions_set[key] = make_region_id(rt, rn)

        soc = record["SOC_Code"]
        if soc not in occupations_set:
            occupations_set[soc] = {
                "name": record["OCC_TITLE"],
                "majorGroupId": record["SOC_Major_Group"],
                "majorGroupName": record["SOC_Major_Group_Name"],
            }

        mg = record["SOC_Major_Group"]
        if mg not in major_groups_set:
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
        # Determine level based on SOC code pattern
        # XX-0000 = major group (level 1), XX-X000 = minor group (level 2), etc.
        if soc_code.endswith("-0000"):
            level = 1
        elif soc_code.endswith("000"):
            level = 2
        elif soc_code.endswith("00"):
            level = 3
        elif soc_code.endswith("0"):
            level = 4
        else:
            level = 5
        occupations.append({
            "socCode": soc_code,
            "name": occ["name"],
            "level": level,
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

    # Build regionData: { regionId: { year: [ {socCode, totEmp, gdp, aMean, complexity} ] } }
    region_data = {}
    for record in raw_data:
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

    # Build aggregates: { year: { byOccupation, minMaxStats } }
    aggregates = {}
    for year in sorted(years):
        year_str = str(year)
        year_records = [r for r in raw_data if r["year"] == year]

        # Aggregate by occupation across all regions
        occ_data = {}
        all_wages = []
        all_complexity = []

        for r in year_records:
            soc = r["SOC_Code"]
            if soc not in occ_data:
                occ_data[soc] = {"totalEmploy": 0, "totalGdp": 0, "wages": [], "complexities": []}
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
                "avgWage": sum(d["wages"]) / len(d["wages"]) if d["wages"] else 0,
                "avgComplexity": sum(d["complexities"]) / len(d["complexities"]) if d["complexities"] else 0,
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
                "medianComplexity": all_complexity_sorted[mid] if all_complexity_sorted else 0.5,
            },
        }

    # Assemble final output
    output = {
        "metadata": {
            "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
            "years": sorted(years),
            "source": "BLS OES + O*NET",
        },
        "regions": regions,
        "occupations": occupations,
        "majorGroups": major_groups,
        "regionData": region_data,
        "aggregates": aggregates,
    }

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    file_size = os.path.getsize(output_path)
    print(f"Wrote {output_path} ({file_size:,} bytes)")
    print(f"  Regions: {len(regions)}")
    print(f"  Occupations: {len(occupations)}")
    print(f"  Major Groups: {len(major_groups)}")
    print(f"  Years: {sorted(years)}")
    print(f"  Region data entries: {sum(len(v) for v in region_data.values())}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate static BLS data for metroverse-jobs")
    parser.add_argument(
        "--input",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "bls2", "data", "job_data.js"),
        help="Path to BLS2 job_data.js file",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "..", "public", "data", "bls-data.json"),
        help="Output path for bls-data.json",
    )
    args = parser.parse_args()

    generate_static_data(args.input, args.output)
