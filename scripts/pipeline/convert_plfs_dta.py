"""Convert PLFS Stata DTA microdata (exported from Nesstar) to the normalized CSV
expected by import_india_subnational_from_microdata().

The DTA files come from exporting the .Nesstar file in Nesstar Explorer as
"Stata 8" format. All years use the same column naming convention.

Usage:
    python scripts/pipeline/convert_plfs_dta.py --dta hh_per_fv_2017-18.dta --year 2018
    python scripts/pipeline/convert_plfs_dta.py --dta hh_per_fv_2017-18.dta --year 2018 --pipeline

Output: data/raw/ind_plfs_microdata.csv (overwritten)

Column mapping (DTA → pipeline):
    state_per_fv    → st         (state/UT code → name)
    b5pt1q6_per_fv  → ocu_pas    (NCO principal occupation code)
    MULT_per_fv     → mult       (sub-sample multiplier, divided by 1000)
    b6q10_per_fv    → ern_reg    (monthly earnings for regular salaried work)
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
MICRO_DIR = RAW_DIR / "plfs_microdata"
OUT_CSV = RAW_DIR / "ind_plfs_microdata.csv"

STATE_CODES = {
    # Must match the 2024 snapshot pipeline (uses "&" not "and")
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

# DTA column candidates — two naming conventions across years:
#   _per_fv  : 2017-18, 2019-20
#   _perv1   : 2020-21 onwards
STATE_CANDIDATES = ["state_per_fv", "state_perv1"]
DIST_CANDIDATES  = ["distcode_per_fv", "distcode_perv1", "b1q4_per_fv", "b1q4_perv1",
                    "dist_code_per_fv", "dist_code_perv1"]
OCU_CANDIDATES   = ["b5pt1q6_per_fv", "b5pt1q6_perv1"]
MULT_CANDIDATES  = ["MULT_per_fv", "mult_perv1", "mult_per_fv"]
ERN_CANDIDATES   = ["b6q10_per_fv", "b6q10_perv1"]

MULT_SCALE = 1000.0  # DTA multipliers are ~1000x actual headcount weight


def convert_dta(dta_path: Path, out_csv: Path) -> int:
    try:
        import pyreadstat
    except ImportError:
        print("Installing pyreadstat...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyreadstat", "-q"])
        import pyreadstat

    print(f"  Reading {dta_path.name} ...")
    df, meta = pyreadstat.read_dta(str(dta_path))
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")

    def pick(candidates):
        return next((c for c in candidates if c in df.columns), None)

    state_col = pick(STATE_CANDIDATES)
    dist_col  = pick(DIST_CANDIDATES)
    ocu_col   = pick(OCU_CANDIDATES)
    mult_col  = pick(MULT_CANDIDATES)
    ern_col   = pick(ERN_CANDIDATES)

    for col, name in [(state_col, "state"), (ocu_col, "occupation"), (mult_col, "multiplier")]:
        if col is None:
            raise ValueError(f"Required {name} column not found. Columns: {list(df.columns[:20])}")

    print(f"  Mapping: state={state_col}  dist={dist_col}  ocu={ocu_col}  mult={mult_col}  ern={ern_col}")

    rows_written = skipped = 0

    with open(out_csv, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=["st", "state_ut_code", "district_code", "ocu_pas", "mult", "ern_reg"])
        writer.writeheader()

        for _, row in df.iterrows():
            state_code = str(row[state_col]).strip().zfill(2)
            ocu = str(row[ocu_col]).strip()
            mult_raw = row[mult_col]

            st_name = STATE_CODES.get(state_code, "")
            if not st_name or not ocu or ocu == "0" or not mult_raw:
                skipped += 1
                continue

            try:
                mult = float(mult_raw) / MULT_SCALE
                if mult <= 0:
                    skipped += 1
                    continue
            except (TypeError, ValueError):
                skipped += 1
                continue

            ern = ""
            if ern_col:
                try:
                    ern_val = float(row[ern_col])
                    if ern_val > 0:
                        ern = str(int(ern_val))
                except (TypeError, ValueError):
                    pass

            dist_code = str(row[dist_col]).strip().zfill(2) if dist_col else ""
            writer.writerow({
                "st": st_name,
                "state_ut_code": state_code,
                "district_code": dist_code,
                "ocu_pas": ocu,
                "mult": f"{mult:.3f}",
                "ern_reg": ern,
            })
            rows_written += 1

    return rows_written


def main():
    parser = argparse.ArgumentParser(description="Convert PLFS Stata DTA microdata to pipeline CSV")
    parser.add_argument("--dta", required=True,
                        help="DTA filename in data/raw/plfs_microdata/ (e.g. hh_per_fv_2017-18.dta)")
    parser.add_argument("--year", type=int, required=True,
                        help="Calendar year (e.g. 2018 for 2017-18)")
    parser.add_argument("--pipeline", action="store_true",
                        help="Also run the India pipeline after conversion")
    args = parser.parse_args()

    dta_path = MICRO_DIR / args.dta
    if not dta_path.exists():
        # Also try just the filename directly
        dta_path = Path(args.dta)
        if not dta_path.exists():
            print(f"ERROR: {MICRO_DIR / args.dta} not found")
            sys.exit(1)

    print(f"Converting {dta_path.name} (year {args.year})...")
    n = convert_dta(dta_path, OUT_CSV)
    print(f"  Written: {n:,} rows -> {OUT_CSV}")

    if n > 0:
        # Write year-specific district labels before pipeline run
        sys.path.insert(0, str(ROOT))
        from scripts.pipeline.plfs_district_labels import write_for_year
        write_for_year(args.year)

        if args.pipeline:
            cmd = [sys.executable, "-m", "scripts.pipeline.run_pipeline",
                   "--year", str(args.year), "--country", "in"]
            print(f"\nRunning pipeline: {' '.join(cmd)}")
            subprocess.run(cmd, cwd=ROOT)
        else:
            print(f"\n  Next: python scripts/pipeline/run_pipeline.py --year {args.year} --country in")


if __name__ == "__main__":
    main()
