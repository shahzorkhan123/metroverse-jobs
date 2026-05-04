"""Convert all available PLFS Stata (.dta) person-level files to the normalized
ind_plfs_microdata.csv and re-run the India pipeline for each year.

Each year's .dta is converted in-place, then the pipeline runs while the CSV
has that year's data. This ensures each year's bls-data-in-{year}.json contains
the actual microdata for that year.

Usage:
    python scripts/pipeline/convert_dta_all_years.py
    python scripts/pipeline/convert_dta_all_years.py --years 2022 2023 2024
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
MICRO_DIR = RAW_DIR / "plfs_microdata"
OUT_CSV = RAW_DIR / "ind_plfs_microdata.csv"

# Calendar year → Stata file (person first-visit)
DTA_FILES = {
    2018: "hh_per_fv_2017-18.dta",
    2020: "PERFV_2019-20.dta",
    2021: "perv1_2020-21.dta",
    2022: "perv1_2021-22.dta",
    2023: "perv1_2022-23.dta",
    2024: "perv1_2023-24.dta",
}

# Calendar year → CSV zip (for years without .dta)
CSV_ZIPS = {
    2019: "PLFS_2018_19_CSV.zip",
}

STATE_CODES = {
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


def _find_col(df_cols: list[str], patterns: list[str]) -> str | None:
    cols_lower = [c.lower() for c in df_cols]
    for pat in patterns:
        for i, c in enumerate(cols_lower):
            if c == pat.lower():
                return df_cols[i]
    for pat in patterns:
        for i, c in enumerate(cols_lower):
            if pat.lower() in c:
                return df_cols[i]
    return None


def dta_to_csv(dta_path: Path, year: int) -> int:
    """Read a Stata .dta person file and write to ind_plfs_microdata.csv."""
    print(f"  Reading {dta_path.name}...")
    df = pd.read_stata(str(dta_path), convert_categoricals=False)
    cols = list(df.columns)

    state_col = _find_col(cols, ["state_per_fv", "state_"])
    ocu_col   = _find_col(cols, ["b5pt1q6_per_fv", "b5pt1q6_"])
    mult_col  = _find_col(cols, ["MULT_per_fv", "mult_per_fv", "mult_"])
    ern_col   = _find_col(cols, ["b6q10_per_fv", "b6q10_"])
    dist_col  = _find_col(cols, ["b1q4_per_fv", "distcode_per_fv", "dist_"])

    print(f"    state={state_col} ocu={ocu_col} mult={mult_col} ern={ern_col} dist={dist_col}")
    if not state_col or not ocu_col or not mult_col:
        raise ValueError(f"Required columns missing in {dta_path.name}")

    rows_written = skipped = 0
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(
            fout,
            fieldnames=["st", "state_ut_code", "district_code", "ocu_pas", "mult", "ern_reg"],
        )
        writer.writeheader()
        for _, row in df.iterrows():
            try:
                raw_state_v = row[state_col]
                raw_state = str(int(float(raw_state_v))).zfill(2) if pd.notna(raw_state_v) and str(raw_state_v).strip() else ""
            except (ValueError, TypeError):
                skipped += 1; continue
            st_name = STATE_CODES.get(raw_state, "")

            try:
                ocu_v = row[ocu_col]
                ocu = str(int(float(ocu_v))) if pd.notna(ocu_v) and str(ocu_v).strip() else ""
            except (ValueError, TypeError):
                skipped += 1; continue

            mult_val = row[mult_col] if pd.notna(row[mult_col]) else None
            if not st_name or not ocu or not mult_val:
                skipped += 1
                continue

            # DTA multipliers use the same 1000x scale as the CSV export format
            # (same as convert_plfs_csv.py which always divides raw CSV values by 1000)
            mult_f = float(mult_val) / 1000.0

            ern = ""
            if ern_col:
                try:
                    ev = row[ern_col]
                    if pd.notna(ev) and str(ev).strip():
                        ern = str(int(float(ev)))
                except (ValueError, TypeError):
                    pass

            dist_code = ""
            if dist_col:
                try:
                    dv = row[dist_col]
                    if pd.notna(dv) and str(dv).strip():
                        dist_code = str(int(float(dv))).zfill(2)
                except (ValueError, TypeError):
                    pass

            writer.writerow({
                "st": st_name,
                "state_ut_code": raw_state,
                "district_code": dist_code,
                "ocu_pas": ocu,
                "mult": str(mult_f),
                "ern_reg": ern,
            })
            rows_written += 1

    print(f"    Written: {rows_written:,}  Skipped: {skipped:,}")
    return rows_written


def run_pipeline(year: int) -> None:
    cmd = [sys.executable, "-m", "scripts.pipeline.run_pipeline",
           "--year", str(year), "--country", "in"]
    print(f"  Running pipeline for {year}...")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-500:]}")
    else:
        # Show key output lines
        for line in result.stdout.splitlines():
            if any(x in line for x in ["State:", "Metro:", "wrote", "Done", "Error"]):
                print(f"    {line.strip()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, nargs="+",
                        default=sorted(set(DTA_FILES) | set(CSV_ZIPS)))
    args = parser.parse_args()

    for year in sorted(args.years):
        print(f"\n{'='*50}")
        print(f"Year {year}")
        print(f"{'='*50}")

        if year in DTA_FILES:
            dta_path = MICRO_DIR / DTA_FILES[year]
            if not dta_path.exists():
                print(f"  SKIP: {dta_path.name} not found")
                continue
            # Also write district labels for this year
            sys.path.insert(0, str(ROOT))
            from scripts.pipeline.plfs_district_labels import write_for_year
            write_for_year(year)
            dta_to_csv(dta_path, year)

        elif year in CSV_ZIPS:
            zip_name = CSV_ZIPS[year]
            zip_path = MICRO_DIR / zip_name
            if not zip_path.exists():
                print(f"  SKIP: {zip_name} not found")
                continue
            # Use existing convert_plfs_csv.py
            from scripts.pipeline.convert_plfs_csv import convert_csv, find_perv1_in_zip
            import zipfile
            with zipfile.ZipFile(zip_path) as z:
                csv_entry = find_perv1_in_zip(z)
                if not csv_entry:
                    print(f"  SKIP: no person CSV found in {zip_name}")
                    continue
                tmp = MICRO_DIR / f"_tmp_{year}.csv"
                with z.open(csv_entry) as src, open(tmp, "wb") as dst:
                    dst.write(src.read())
            try:
                convert_csv(tmp, year, OUT_CSV)
            finally:
                tmp.unlink(missing_ok=True)
            sys.path.insert(0, str(ROOT))
            from scripts.pipeline.plfs_district_labels import write_for_year
            write_for_year(year)

        run_pipeline(year)

    print("\nAll years done.")


if __name__ == "__main__":
    main()
