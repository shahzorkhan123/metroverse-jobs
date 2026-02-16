"""Generate data/job_data.js (JSONP) from SQLite."""

import json
import sqlite3
from datetime import date
from pathlib import Path

from . import config


def _query_records(conn: sqlite3.Connection,
                   country_codes: list[str] | None = None) -> list[dict]:
    """Query occupation records and map to frontend contract.

    DB column              -> JS field
    occupation_code        -> SOC_Code
    occupation_title       -> OCC_TITLE
    major_group_name       -> SOC_Major_Group_Name
    employment             -> TOT_EMP
    mean_annual_wage       -> A_MEAN
    gdp                    -> GDP
    region.region_type     -> Region_Type  (uses "Metro")
    region.name            -> Region
    """
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

    records = []
    for row in conn.execute(query, params).fetchall():
        (year, region_type, region, occ_code, occ_title, major_group,
         employment, wage, gdp, complexity, _country_code) = row

        # Extract SOC major group prefix (first 2 digits)
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


def _build_metadata(records: list[dict]) -> dict:
    """Build metadata for dropdown controls from the record set."""
    years = sorted(set(r["year"] for r in records))
    region_types = sorted(set(r["Region_Type"] for r in records))

    regions_by_type: dict[str, list[str]] = {}
    for r in records:
        rt = r["Region_Type"]
        rn = r["Region"]
        if rt not in regions_by_type:
            regions_by_type[rt] = []
        if rn not in regions_by_type[rt]:
            regions_by_type[rt].append(rn)

    # Sort region lists
    for rt in regions_by_type:
        regions_by_type[rt].sort()

    return {
        "years": years,
        "regionTypes": region_types,
        "parameters": ["complexity", "employment", "wage"],
        "limits": ["all", "top50"],
        "regions": regions_by_type,
    }


def export_jsonp(conn: sqlite3.Connection,
                 country_codes: list[str] | None = None,
                 output_path: Path | None = None) -> int:
    """Generate the JSONP file. Returns record count."""
    if output_path is None:
        output_path = config.JSONP_PATH

    records = _query_records(conn, country_codes)
    metadata = _build_metadata(records)
    today = date.today().isoformat()

    # Build the JSONP content
    job_data_json = json.dumps(records, indent=8)
    metadata_json = json.dumps(metadata, indent=8)

    content = f"""/**
 * Job data for BLS Visualizations
 * This file contains embedded job data in JSONP format to avoid CORS issues
 * Format: Static JavaScript data for CORS-free access
 * Last updated: {today}
 * Records: {len(records)}
 */

// Embedded job data - CORS-free approach
window.BLS_DATA = {{
    lastUpdated: '{today}',
    dataSource: 'BLS OES Data + O*NET Complexity Scores',

    // Main dataset - embedded directly to avoid CORS issues
    jobData: {job_data_json},

    // Simple synchronous data access - no CORS issues
    getData() {{
        console.log('BLS Data loaded successfully - ', this.jobData.length, 'records available');
        return this.jobData;
    }},

    // Metadata for dropdown controls and filtering
    metadata: {metadata_json}
}};

// Helper function to get data (synchronous - no CORS issues)
window.getBLSData = function() {{
    return window.BLS_DATA.getData();
}};

// Helper function to get metadata
window.getBLSMetadata = function() {{
    return window.BLS_DATA.metadata;
}};

// Helper function for external updates (used by Python scripts)
window.updateBLSData = function(newData, newMetadata) {{
    window.BLS_DATA.jobData = newData;
    if (newMetadata) {{
        window.BLS_DATA.metadata = newMetadata;
    }}
    window.BLS_DATA.lastUpdated = new Date().toISOString().split('T')[0];

    // Trigger update event for listening components
    const event = new CustomEvent('blsDataUpdated', {{
        detail: {{ data: newData, metadata: newMetadata }}
    }});
    document.dispatchEvent(event);
}};

console.log('BLS Data loader initialized - use getBLSData() to access embedded data (CORS-free)');
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return len(records)
