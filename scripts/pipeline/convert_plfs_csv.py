"""Convert PLFS CSV-format microdata (2018-19, 2021-22) to the normalized CSV
expected by import_india_subnational_from_microdata().

Handles two CSV naming conventions from MoSPI downloads:
  - PerV1_2018-19.csv  (2018-19): columns like b5pt1q6_per_fv, MULT_per_fv
  - cperv1.csv        (2021-22): columns like b5pt1q6_cperv1, mult_cperv1

For Nesstar-format years (2017-18, 2019-20, 2020-21, 2022-23, 2023-24):
  Use NesstarExplorer (included in each zip) to export as CSV, then run this.

Usage:
    python scripts/pipeline/convert_plfs_csv.py --zip PLFS_2018_19_CSV.zip --year 2019
    python scripts/pipeline/convert_plfs_csv.py --zip PLFS_Data_2022-22_CSV.zip --year 2022
"""

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
MICRO_DIR = RAW_DIR / "plfs_microdata"
OUT_CSV = RAW_DIR / "ind_plfs_microdata.csv"

# State code → name (from Data_LayoutPLFS_2023-24.xlsx State code sheet)
STATE_CODES = {
    # Names must match the 2024 snapshot pipeline (uses "&" not "and")
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
    "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar Islands",
    "36": "Telangana", "37": "Ladakh",
}

# Column detection: patterns for each needed field
# Each entry: list of possible column name substrings to match
FIELD_PATTERNS = {
    "state":    ["state_per_fv", "state_cperv1", "state_perv1", "state_"],
    "dist":     ["distcode_per_fv", "distcode_cperv1", "distcode_perv1",
                 "b1q4_per_fv", "b1q4_cperv1", "dist_code"],
    "ocu_pas":  ["b5pt1q6_per_fv", "b5pt1q6_cperv1", "b5pt1q6_perv1",
                 "b5pt1q6", "ocu_pas"],
    "mult":     ["mult_per_fv", "mult_cperv1", "mult_perv1", "MULT_per_fv", "mult"],
    "ern_reg":  ["b6q10_cperv1", "b6q10_per_fv", "b6q10_perv1", "ern_reg", "b6q10"],
}


def find_col(headers: list[str], patterns: list[str]) -> int | None:
    """Find column index by trying patterns in order."""
    headers_lower = [h.lower() for h in headers]
    for pat in patterns:
        pat_lower = pat.lower()
        for i, h in enumerate(headers_lower):
            if h == pat_lower:
                return i
    # Partial match fallback
    for pat in patterns:
        pat_lower = pat.lower()
        for i, h in enumerate(headers_lower):
            if pat_lower in h:
                return i
    return None


def convert_csv(src_path: str | Path, year: int, out_csv: Path) -> int:
    """Convert a PLFS person-level CSV to normalized pipeline format."""
    rows_written = skipped = 0

    with open(src_path, "r", encoding="latin-1", errors="replace") as fin:
        reader = csv.reader(fin)
        headers = next(reader)

        state_col = find_col(headers, FIELD_PATTERNS["state"])
        dist_col  = find_col(headers, FIELD_PATTERNS["dist"])
        ocu_col   = find_col(headers, FIELD_PATTERNS["ocu_pas"])
        mult_col  = find_col(headers, FIELD_PATTERNS["mult"])
        ern_col   = find_col(headers, FIELD_PATTERNS["ern_reg"])

        print(f"  Columns: state={state_col} dist={dist_col} ocu={ocu_col} mult={mult_col} ern={ern_col}")

        if state_col is None or ocu_col is None or mult_col is None:
            raise ValueError("Could not find required columns (state, occupation, multiplier)")

        with open(out_csv, "w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=["st", "state_ut_code", "district_code", "ocu_pas", "mult", "ern_reg"])
            writer.writeheader()

            for row in reader:
                if len(row) <= max(c for c in [state_col, ocu_col, mult_col] if c is not None):
                    skipped += 1
                    continue

                raw_state = row[state_col].strip().zfill(2)
                st_name = STATE_CODES.get(raw_state, "")
                ocu = row[ocu_col].strip()
                mult = row[mult_col].strip()

                if not st_name or not ocu or not mult or mult in ("", "0", "."):
                    skipped += 1
                    continue

                ern = ""
                if ern_col is not None and ern_col < len(row):
                    ern = row[ern_col].strip()

                dist_code = ""
                if dist_col is not None and dist_col < len(row):
                    dist_code = row[dist_col].strip().zfill(2)

                # CSV multipliers are stored ~1000x the actual headcount weight.
                try:
                    scaled_mult = str(float(mult) / 1000.0)
                except ValueError:
                    scaled_mult = mult

                writer.writerow({
                    "st": st_name,
                    "state_ut_code": raw_state,
                    "district_code": dist_code,
                    "ocu_pas": ocu,
                    "mult": scaled_mult,
                    "ern_reg": ern,
                })
                rows_written += 1

    print(f"  Written: {rows_written:,} rows  Skipped: {skipped:,}")
    return rows_written


def find_perv1_in_zip(z: zipfile.ZipFile) -> str | None:
    """Find the person visit 1 CSV inside a zip."""
    candidates = []
    for name in z.namelist():
        nl = name.lower()
        if nl.endswith('.csv') and any(p in nl for p in ['perv1', 'perv1_', 'per_v1', 'per v1']):
            candidates.append(name)
    return candidates[0] if candidates else None


def main():
    parser = argparse.ArgumentParser(description="Convert PLFS CSV microdata to pipeline format")
    parser.add_argument("--zip", required=True,
                        help="Zip filename in data/raw/plfs_microdata/ (e.g. PLFS_2018_19_CSV.zip)")
    parser.add_argument("--year", type=int, required=True,
                        help="Calendar year of data (e.g. 2019 for 2018-19)")
    parser.add_argument("--pipeline", action="store_true",
                        help="Also run the India pipeline after conversion")
    args = parser.parse_args()

    zip_path = MICRO_DIR / args.zip
    if not zip_path.exists():
        print(f"ERROR: {zip_path} not found")
        sys.exit(1)

    print(f"Converting {args.zip} (year {args.year})...")

    with zipfile.ZipFile(zip_path) as z:
        csv_entry = find_perv1_in_zip(z)
        if not csv_entry:
            print(f"No person-level CSV found. Available files:")
            for n in z.namelist():
                if n.endswith('.csv'):
                    print(f"  {n}")
            sys.exit(1)

        print(f"  Extracting: {csv_entry}")
        tmp_path = MICRO_DIR / f"_tmp_perv1_{args.year}.csv"
        with z.open(csv_entry) as src, open(tmp_path, "wb") as dst:
            dst.write(src.read())

    try:
        n = convert_csv(tmp_path, args.year, OUT_CSV)
    finally:
        tmp_path.unlink(missing_ok=True)

    if n > 0:
        print(f"  Output: {OUT_CSV}")
        sys.path.insert(0, str(ROOT))
        from scripts.pipeline.plfs_district_labels import write_for_year
        write_for_year(args.year)
        if args.pipeline:
            import subprocess
            cmd = [sys.executable, "-m", "scripts.pipeline.run_pipeline",
                   "--year", str(args.year), "--country", "in"]
            print(f"\nRunning pipeline: {' '.join(cmd)}")
            subprocess.run(cmd, cwd=ROOT)
        else:
            print(f"\n  Next: python scripts/pipeline/run_pipeline.py --year {args.year} --country in")


if __name__ == "__main__":
    main()
