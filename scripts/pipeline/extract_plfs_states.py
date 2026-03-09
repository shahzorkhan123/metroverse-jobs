"""Extract state-level PLFS data from annual report PDFs.

Extracts two tables from each year's PDF:
1. Employment % distribution by NCO division × State (Table 25 equivalent)
2. Average wages by NCO division × State (Table 50/33/55 equivalent)

Uses PyPDF2 for fast page scanning, pdfplumber for targeted table extraction.

Usage:
    python scripts/pipeline/extract_plfs_states.py
"""

import json
import os
import re
import sys
from pathlib import Path

from PyPDF2 import PdfReader

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "public" / "data"

YEARS = [
    ("2017_18", 2018),
    ("2018_19", 2019),
    ("2019_20", 2020),
    ("2020_21", 2021),
    ("2021_22", 2022),
    ("2022_23", 2023),
    ("2023_24", 2024),
]

# Standard state name normalization
STATE_ALIASES = {
    "andhra pradesh": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "delhi": "Delhi",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jammu & kashmir": "Jammu & Kashmir",
    "jammu and kashmir": "Jammu & Kashmir",
    "jammu &kashmir": "Jammu & Kashmir",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "tamilnadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttarakhand": "Uttarakhand",
    "uttar pradesh": "Uttar Pradesh",
    "west bengal": "West Bengal",
    "andaman & nicobar islands": "Andaman & Nicobar Islands",
    "andaman & n. island": "Andaman & Nicobar Islands",
    "andaman &nicobar islands": "Andaman & Nicobar Islands",
    "chandigarh": "Chandigarh",
    "dadra & nagar haveli": "Dadra & Nagar Haveli",
    "dadra &nagar haveli": "Dadra & Nagar Haveli",
    "dadra & nagar haveli & daman & diu": "Dadra & Nagar Haveli",
    "daman & diu": "Daman & Diu",
    "d & n. haveli & daman & diu": "Dadra & Nagar Haveli",
    "d &n. haveli & daman & diu": "Dadra & Nagar Haveli",
    "lakshadweep": "Lakshadweep",
    "puducherry": "Puducherry",
    "pondicherry": "Puducherry",
    "ladakh": "Ladakh",
    "all india": None,  # Skip national row
}


def _normalize_state(name: str) -> str | None:
    """Normalize state name, return None for non-state rows."""
    clean = name.strip().lower()
    # Remove leading numbers/bullets
    clean = re.sub(r"^\d+[\.\)]\s*", "", clean)
    if clean in STATE_ALIASES:
        return STATE_ALIASES[clean]
    # Try partial match
    for alias, canonical in STATE_ALIASES.items():
        if alias in clean or clean in alias:
            return canonical
    return None


def _find_pages_pyp(reader: PdfReader, keywords: list[str],
                     start_frac: float = 0.5) -> list[int]:
    """Fast page scan using PyPDF2 text extraction."""
    total = len(reader.pages)
    start = max(0, int(total * start_frac))
    pages = []
    for i in range(start, total):
        text = (reader.pages[i].extract_text() or "").lower()
        if all(kw in text for kw in keywords):
            pages.append(i)
    return pages


def _extract_state_table_plumber(pdf_path: str, page_nums: list[int],
                                  value_type: str = "float") -> dict:
    """Extract state × NCO division table from specific pages using pdfplumber.

    Returns: { state_name: { "1": val, "2": val, ..., "9": val } }
    """
    import pdfplumber

    result = {}
    pdf = pdfplumber.open(pdf_path)

    for pi in page_nums:
        if pi >= len(pdf.pages):
            continue
        page = pdf.pages[pi]
        tables = page.extract_tables()

        for table in tables:
            if not table or len(table) < 3:
                continue

            for row in table:
                if not row or len(row) < 10:
                    continue

                cell0 = str(row[0] or "").strip()
                state = _normalize_state(cell0)
                if state is None:
                    continue

                # Extract columns 1-9 (NCO divisions)
                vals = {}
                for ci in range(1, min(len(row), 10)):
                    raw = str(row[ci] or "").replace(",", "").strip()
                    try:
                        vals[str(ci)] = float(raw)
                    except (ValueError, TypeError):
                        pass

                if len(vals) >= 5:  # Need at least 5 divisions
                    result[state] = vals

    pdf.close()
    return result


def extract_employment_pct(pdf_path: str, year_label: str) -> dict:
    """Extract state-level employment % by NCO division."""
    reader = PdfReader(pdf_path)

    # Look for the % distribution by occupation table
    # Different years use different table titles
    pages = _find_pages_pyp(reader, ["percentage distribution", "occupation"])
    if not pages:
        pages = _find_pages_pyp(reader, ["percentage distribution", "nco"])

    if not pages:
        print(f"    {year_label}: No employment % table found")
        return {}

    # Filter to pages that have state names (not just national summary)
    state_pages = []
    for pi in pages:
        text = (reader.pages[pi].extract_text() or "").lower()
        # Must have actual state names
        if any(s in text for s in ["andhra", "bihar", "gujarat", "maharashtra", "tamil"]):
            state_pages.append(pi)

    if not state_pages:
        # Try the pages themselves
        state_pages = pages[:10]  # Limit to avoid slowness

    print(f"    {year_label}: Found {len(state_pages)} employment % pages")
    data = _extract_state_table_plumber(pdf_path, state_pages)
    print(f"    {year_label}: Extracted {len(data)} states")
    return data


def extract_wages(pdf_path: str, year_label: str) -> dict:
    """Extract state-level wages by NCO division."""
    reader = PdfReader(pdf_path)

    # Look for wage/salary earnings by occupation table
    pages = _find_pages_pyp(reader, ["wage/salary earnings", "occupation"])
    if not pages:
        pages = _find_pages_pyp(reader, ["wage", "nco"])

    if not pages:
        print(f"    {year_label}: No wage table found")
        return {}

    # Filter to state-level pages
    state_pages = []
    for pi in pages:
        text = (reader.pages[pi].extract_text() or "").lower()
        if any(s in text for s in ["andhra", "bihar", "gujarat", "maharashtra"]):
            # Also must be rural+urban person (not just male/female/rural/urban)
            if "rural+urban" in text or "rural + urban" in text:
                state_pages.append(pi)

    if not state_pages:
        state_pages = pages[:10]

    print(f"    {year_label}: Found {len(state_pages)} wage pages")
    data = _extract_state_table_plumber(pdf_path, state_pages)
    print(f"    {year_label}: Extracted {len(data)} states")
    return data


def main():
    print("=== PLFS State-Level Data Extraction ===\n")

    all_emp_pct = {}   # { year: { state: { div: pct } } }
    all_wages = {}     # { year: { state: { div: wage } } }

    for suffix, cal_year in YEARS:
        pdf_path = RAW_DIR / f"plfs_{suffix}_annual.pdf"
        if not pdf_path.exists():
            print(f"  {suffix}: PDF not found, skipping")
            continue

        label = f"{cal_year - 1}-{str(cal_year)[-2:]}"
        print(f"\n  Processing {label}...")

        emp = extract_employment_pct(str(pdf_path), label)
        if emp:
            all_emp_pct[cal_year] = emp

        wages = extract_wages(str(pdf_path), label)
        if wages:
            all_wages[cal_year] = wages

    # Save intermediate results
    out = {"employment_pct": all_emp_pct, "wages": all_wages}
    out_path = RAW_DIR / "plfs_state_extracted.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved to {out_path}")

    # Summary
    print("\n  Summary:")
    for cal_year in sorted(set(list(all_emp_pct.keys()) + list(all_wages.keys()))):
        fy = f"{cal_year - 1}-{str(cal_year)[-2:]}"
        emp_count = len(all_emp_pct.get(cal_year, {}))
        wage_count = len(all_wages.get(cal_year, {}))
        print(f"    {fy}: {emp_count} states (emp%), {wage_count} states (wages)")


if __name__ == "__main__":
    main()
