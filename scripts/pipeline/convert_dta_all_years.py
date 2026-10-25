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
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from scripts.pipeline.config import INDIA_STATE_CODE_TO_NAME  # noqa: E402
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

# Canonical "and" names (codes 25/26 both map to the merged DNH & DD UT)
STATE_CODES = INDIA_STATE_CODE_TO_NAME

# Daily casual wage columns for the 7 CWS days x 2 activities; naming varies by
# year (b6q9_3pt1_Act1_per_fv, b6q9_act2_3pt1_perv1, b6q9_Act2_3pt7, ...)
CASUAL_WAGE_RX = re.compile(r"^b6q9_.*3pt[1-7]", re.IGNORECASE)
WORKER_STATUS = (11, 51)  # usual status codes 11-51 = employed
DAYS_PER_MONTH = 365.0 / 12.0


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


def _num(df: pd.DataFrame, col: str | None) -> pd.Series:
    if not col:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").astype("float64")


def frame_to_csv(df: pd.DataFrame, source_name: str) -> int:
    """Normalize a PLFS first-visit person frame and write ind_plfs_microdata.csv.

    - Weight: official PLFS annual rule, MULT / (No_qtr x 100) when NSS == NSC,
      else MULT / (No_qtr x 200). Reproduces the published 2023-24 WPR (43.7%).
    - Workers: usual status (principal + subsidiary). Occupation is the principal
      NCO for principal-status workers, else the subsidiary NCO.
    - Earnings (monthly INR, CWS): regular salaried (b6q9) if > 0, else
      self-employed gross (b6q10), else 7-day casual wages scaled to a month.
    """
    cols = list(df.columns)
    state_col = _find_col(cols, ["state_per_fv", "state_perv1", "state_"])
    ps_status = _find_col(cols, ["b5pt1q3_per_fv", "b5pt1q3_perv1", "b5pt1q3"])
    ps_nco    = _find_col(cols, ["b5pt1q6_per_fv", "b5pt1q6_perv1", "b5pt1q6"])
    ss_status = _find_col(cols, ["b5pt2q3_per_fv", "b5pt2q3_perv1", "b5pt2q3"])
    ss_nco    = _find_col(cols, ["b5pt2q6_per_fv", "b5pt2q6_perv1", "b5pt2q6"])
    mult_col  = _find_col(cols, ["MULT_per_fv", "mult_perv1", "mult_"])
    nss_col   = _find_col(cols, ["NSS_per_fv", "NSS_perv1"])
    nsc_col   = _find_col(cols, ["NSC_per_fv", "NSC_perv1"])
    qtr_col   = _find_col(cols, ["No_qtr_per_fv", "no_qtr_perv1", "no_qtr"])
    reg_col   = _find_col(cols, ["b6q9_per_fv", "b6q9_perv1"])
    se_col    = _find_col(cols, ["b6q10_per_fv", "b6q10_perv1"])
    dist_col  = _find_col(cols, ["b1q4_per_fv", "distcode_per_fv", "distcode_perv1", "dist_"])
    casual_cols = [c for c in cols if CASUAL_WAGE_RX.match(c)]

    print(f"    state={state_col} ps={ps_status}/{ps_nco} ss={ss_status}/{ss_nco} "
          f"mult={mult_col} nss/nsc/qtr={nss_col}/{nsc_col}/{qtr_col} "
          f"reg={reg_col} se={se_col} casual_cols={len(casual_cols)} dist={dist_col}")
    required = [state_col, ps_status, ps_nco, mult_col, nss_col, nsc_col, qtr_col]
    if not all(required):
        raise ValueError(f"Required columns missing in {source_name}")

    mult = _num(df, mult_col)
    no_qtr = _num(df, qtr_col)
    divisor = np.where(_num(df, nss_col) == _num(df, nsc_col), 100.0, 200.0) * no_qtr
    weight = mult / divisor

    lo, hi = WORKER_STATUS
    ps_worker = _num(df, ps_status).between(lo, hi)
    ss_worker = ~ps_worker & _num(df, ss_status).between(lo, hi)
    nco = _num(df, ps_nco).where(ps_worker)
    nco = nco.fillna(_num(df, ss_nco).where(ss_worker))

    reg = _num(df, reg_col)
    se = _num(df, se_col)
    casual_week = df[casual_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
    earnings = reg.where(reg > 0)
    earnings = earnings.fillna(se.where(se > 0))
    earnings = earnings.fillna((casual_week * DAYS_PER_MONTH / 7.0).where(casual_week > 0))

    state_code = _num(df, state_col)
    out = pd.DataFrame({
        "state_ut_code": state_code.map(lambda v: f"{int(v):02d}" if pd.notna(v) else ""),
        "district_code": _num(df, dist_col).map(lambda v: f"{int(v):02d}" if pd.notna(v) else ""),
        "ocu_pas": nco.map(lambda v: str(int(v)) if pd.notna(v) else ""),
        "mult": weight,
        "ern_reg": earnings.round().map(lambda v: str(int(v)) if pd.notna(v) else ""),
    })
    out.insert(0, "st", out["state_ut_code"].map(STATE_CODES).fillna(""))

    # Workers only: the importer's district filter (>= 1M) then counts workers,
    # which intentionally keeps metro output small.
    keep = (out["st"] != "") & (out["ocu_pas"] != "") & (out["mult"] > 0)
    out = out[keep]
    out.to_csv(OUT_CSV, index=False, encoding="utf-8")

    pop = weight[weight > 0].sum()
    print(f"    Population {pop / 1e6:,.1f}M  Workers (PS+SS) {out['mult'].sum() / 1e6:,.1f}M  "
          f"Written: {len(out):,}  Skipped: {len(df) - len(out):,}")
    return len(out)


def dta_to_csv(dta_path: Path, year: int) -> int:
    """Read a Stata .dta person file and write to ind_plfs_microdata.csv."""
    print(f"  Reading {dta_path.name}...")
    df = pd.read_stata(str(dta_path), convert_categoricals=False)
    return frame_to_csv(df, dta_path.name)


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
            from scripts.pipeline.plfs_district_labels import write_for_year
            write_for_year(year)
            dta_to_csv(dta_path, year)

        elif year in CSV_ZIPS:
            zip_name = CSV_ZIPS[year]
            zip_path = MICRO_DIR / zip_name
            if not zip_path.exists():
                print(f"  SKIP: {zip_name} not found")
                continue
            from scripts.pipeline.convert_plfs_csv import find_perv1_in_zip
            import zipfile
            with zipfile.ZipFile(zip_path) as z:
                csv_entry = find_perv1_in_zip(z)
                if not csv_entry:
                    print(f"  SKIP: no person CSV found in {zip_name}")
                    continue
                print(f"  Reading {csv_entry}...")
                with z.open(csv_entry) as src:
                    df = pd.read_csv(src, dtype=str, low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            frame_to_csv(df, csv_entry)
            from scripts.pipeline.plfs_district_labels import write_for_year
            write_for_year(year)

        run_pipeline(year)

    print("\nAll years done.")


if __name__ == "__main__":
    main()
