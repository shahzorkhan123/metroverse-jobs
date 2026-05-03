"""Write the correct year's PLFS district labels CSV.

PLFS uses a rotating panel design — district codes change across survey panels:
  Panel 1: 2017-18, 2018-19  (District_codes_PLFS_Panel_1_201718_201819.xlsx)
  Panel 2: 2019-20, 2020-21  (District_codes_PLFS_Panel_2_201920_202021.xlsx)
  Panel 3: 2021-22, 2022-23  (District_codes_PLFS_Panel_3_202122_202223.xlsx)
  2023-24+: 5. Indian_Districts_Code  Name.xlsx

Call write_for_year(year) before running the India pipeline for a given year.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
MICRO_DIR = RAW_DIR / "plfs_microdata"
OUT_CSV = RAW_DIR / "ind_district_labels.csv"

PANEL_FILES = {
    2018: "District_codes_PLFS_Panel_1_201718_201819.xlsx",
    2019: "District_codes_PLFS_Panel_1_201718_201819.xlsx",
    2020: "District_codes_PLFS_Panel_2_201920_202021.xlsx",
    2021: "District_codes_PLFS_Panel_2_201920_202021.xlsx",
    2022: "District_codes_PLFS_Panel_3_202122_202223.xlsx",
    2023: "District_codes_PLFS_Panel_3_202122_202223.xlsx",
    2024: "5. Indian_Districts_Code  Name.xlsx",
    2025: "5. Indian_Districts_Code  Name.xlsx",  # same file for now
}


def write_for_year(year: int) -> int:
    """Write ind_district_labels.csv for the given survey year.
    Returns number of districts written, or 0 if source not found.
    """
    fname = PANEL_FILES.get(year)
    if not fname:
        print(f"  [district labels] No panel file defined for year {year}")
        return 0

    src = MICRO_DIR / fname
    if not src.exists():
        print(f"  [district labels] Source not found: {src.name}")
        return 0

    try:
        import openpyxl
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl", "-q"])
        import openpyxl

    wb = openpyxl.load_workbook(str(src), read_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))

    # Find header row (contains "State Code" or similar)
    header_idx = next(
        (i for i, r in enumerate(rows)
         if r and any(str(c or "").lower() in ("state code", "state_code") for c in r)),
        None,
    )
    if header_idx is None:
        print(f"  [district labels] Header not found in {src.name}")
        return 0

    count = 0
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["state_code", "district_code", "name"])
        writer.writeheader()
        for row in rows[header_idx + 1:]:
            if not row or not row[0] or not row[2] or not row[3]:
                continue
            sc   = str(row[0]).strip().zfill(2)
            dc   = str(row[2]).strip().zfill(2)
            name = str(row[3]).strip()
            if sc and dc and name:
                writer.writerow({"state_code": sc, "district_code": dc, "name": name})
                count += 1

    print(f"  [district labels] {src.name} -> {count} districts for year {year}")
    return count
