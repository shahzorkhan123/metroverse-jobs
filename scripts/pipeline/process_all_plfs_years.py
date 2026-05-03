"""Process all available PLFS microdata years end-to-end.

For each year directory found in data/raw/plfs_microdata/YYYY/:
  1. Converts perv1.txt → data/raw/ind_plfs_microdata.csv
  2. Runs the India pipeline for that year
  3. Rebuilds data/analysis.db

Usage:
    python scripts/pipeline/process_all_plfs_years.py
    python scripts/pipeline/process_all_plfs_years.py --years 2021 2022 2023
    python scripts/pipeline/process_all_plfs_years.py --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MICRO_DIR = ROOT / "data" / "raw" / "plfs_microdata"


def run(cmd, check=True):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run([str(c) for c in cmd], cwd=ROOT)
    if check and result.returncode != 0:
        print(f"  ERROR: exit code {result.returncode}")
        sys.exit(result.returncode)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Process all PLFS microdata years")
    parser.add_argument("--years", type=int, nargs="+",
                        help="Specific years to process (default: all found)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without executing")
    parser.add_argument("--skip-rebuild-db", action="store_true",
                        help="Skip final analysis.db rebuild")
    args = parser.parse_args()

    if args.years:
        years = sorted(args.years)
    else:
        years = sorted(
            int(p.name) for p in MICRO_DIR.iterdir()
            if p.is_dir() and p.name.isdigit() and (p / "perv1.txt").exists()
        )

    if not years:
        print(f"No year directories with perv1.txt found in {MICRO_DIR}")
        print("See data/raw/plfs_microdata/README.md for download instructions.")
        sys.exit(1)

    print(f"Processing {len(years)} year(s): {years}\n")

    for year in years:
        txt = MICRO_DIR / str(year) / "perv1.txt"
        if not txt.exists():
            print(f"[{year}] SKIP — perv1.txt not found at {txt}")
            continue

        size_mb = txt.stat().st_size / 1e6
        print(f"\n[{year}] perv1.txt ({size_mb:.0f} MB)")

        convert_cmd = [
            sys.executable, "scripts/pipeline/convert_plfs_microdata.py",
            "--year", str(year),
        ]
        pipeline_cmd = [
            sys.executable, "-m", "scripts.pipeline.run_pipeline",
            "--year", str(year), "--country", "in",
        ]

        if args.dry_run:
            print(f"  Would run: {' '.join(str(c) for c in convert_cmd)}")
            print(f"  Would run: {' '.join(str(c) for c in pipeline_cmd)}")
            continue

        print(f"  Step 1/2: Converting microdata...")
        run(convert_cmd)

        print(f"  Step 2/2: Running India pipeline for {year}...")
        run(pipeline_cmd)

    if not args.dry_run and not args.skip_rebuild_db:
        print("\nRebuilding analysis.db...")
        run([sys.executable, "scripts/rebuild_analysis_db.py", "--verify"])

    print("\nDone.")


if __name__ == "__main__":
    main()
