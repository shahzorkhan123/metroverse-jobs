"""CLI orchestrator for the BLS data pipeline."""

import argparse
import sys
from pathlib import Path

# Add project root to path so we can run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.pipeline import (
    config, db, import_csv, export_csv, export_json, export_jsonp,
    export_split, validate,
)


def main():
    parser = argparse.ArgumentParser(
        description="BLS Data Pipeline: Fetch -> Import -> Compute -> Export"
    )
    parser.add_argument(
        "--year", type=int, default=2024,
        help="Data year (default: 2024)",
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Drop and recreate all tables before import",
    )
    parser.add_argument(
        "--fetch", action="store_true",
        help="Download BLS + O*NET data before import",
    )
    parser.add_argument(
        "--import-only", action="store_true",
        help="Only import CSVs into SQLite (skip export)",
    )
    parser.add_argument(
        "--export-only", action="store_true",
        help="Only export from existing SQLite (skip import)",
    )
    parser.add_argument(
        "--country", type=str, default="us",
        help="Country short code for output filenames (default: us)",
    )
    parser.add_argument(
        "--export-country", nargs="+", default=None,
        help="Country codes to include in export (default: USA only)",
    )
    parser.add_argument(
        "--export-json", action="store_true", default=True,
        help="Generate frontend JSON files (default: on)",
    )
    parser.add_argument(
        "--no-export-json", dest="export_json", action="store_false",
        help="Skip generating frontend JSON files",
    )
    parser.add_argument(
        "--export-csv", action="store_true", default=False,
        help="Generate research CSV files",
    )
    parser.add_argument(
        "--split-levels", action="store_true", default=True,
        help="Generate per-level split JSON files (default: on)",
    )
    parser.add_argument(
        "--no-split-levels", dest="split_levels", action="store_false",
        help="Skip generating per-level split JSON files",
    )
    parser.add_argument(
        "--skip-jsonp", action="store_true", default=True,
        help="Skip generating JSONP file (default: skip)",
    )
    parser.add_argument(
        "--export-jsonp", dest="skip_jsonp", action="store_false",
        help="Also generate JSONP file (for bls2 compatibility)",
    )
    parser.add_argument(
        "--db-path", type=str, default=None,
        help=f"SQLite database path (default: {config.DB_PATH})",
    )

    args = parser.parse_args()
    db_path = Path(args.db_path) if args.db_path else config.DB_PATH
    export_countries = args.export_country or ["USA"]
    # Map short country code to 3-letter code for DB queries
    _short_to_long = {v: k for k, v in
                      {k: config.country_short(k) for k in config.COUNTRIES}.items()}
    country_long = _short_to_long.get(args.country.lower(), "USA")

    print("=== BLS Data Pipeline ===")
    print(f"  Year: {args.year}")
    print(f"  Country: {args.country} ({country_long})")
    print(f"  DB: {db_path}")
    print(f"  Export countries: {', '.join(export_countries)}")
    if args.fetch:
        print("  Mode: fetch + import + export")
    elif args.import_only:
        print("  Mode: import only")
    elif args.export_only:
        print("  Mode: export only")
    else:
        print("  Mode: import + export")
    print()

    # --- FETCH PHASE ---
    combined_csv_path = None
    if args.fetch:
        print("--- FETCH PHASE ---\n")
        try:
            from scripts.pipeline import fetch_bls
            combined_csv_path = fetch_bls.fetch_and_parse(args.year)
            print()
        except ImportError as e:
            print(f"  ERROR: Missing dependency for fetch: {e}")
            print("  Install with: pip install requests openpyxl pandas")
            sys.exit(1)
        except Exception as e:
            print(f"  ERROR fetching BLS data: {e}")
            sys.exit(1)

        # Optionally fetch O*NET data
        try:
            from scripts.pipeline import fetch_onet
            print("Fetching O*NET complexity data...")
            fetch_onet.fetch_and_compute_complexity()
            print()
        except ImportError as e:
            print(f"  WARNING: Skipping O*NET fetch (missing: {e})")
        except Exception as e:
            print(f"  WARNING: O*NET fetch failed: {e}")
            print("  Continuing with GDP-based complexity placeholder...")

    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(db_path)

    try:
        # --- IMPORT PHASE ---
        if not args.export_only:
            if args.fresh:
                print("Dropping existing tables...")
                db.drop_all(conn)

            print("Creating schema...")
            db.create_schema(conn)

            print(f"\nImporting data for year {args.year}...")

            if combined_csv_path and combined_csv_path.exists():
                # Import from fetched combined CSV
                total = import_csv.import_combined_csv(
                    conn, combined_csv_path, args.year
                )
            else:
                # Import from individual CSV files (legacy bls2 format)
                total = import_csv.import_all(conn, args.year)

            conn.commit()
            print(f"\nTotal imported: {total} records")

            print("\nComputing complexity scores (GDP normalization)...")
            db.compute_complexity_scores(conn)

            # Validate DB
            print("\nValidating database...")
            errors = validate.validate_db(conn)
            if errors:
                print("  VALIDATION ERRORS:")
                for e in errors:
                    print(f"    - {e}")
            else:
                print("  Database validation passed")

            # Print summary
            print("\nSummary:")
            for row in db.get_summary(conn):
                print(f"  {row['country_code']} {row['region_type']}: "
                      f"{row['record_count']} records")

        if args.import_only:
            print("\n--import-only: skipping export")
            return

        # --- EXPORT PHASE ---
        print("\n--- EXPORT PHASE ---\n")

        if args.export_csv:
            print("Exporting intermediate CSVs...")
            csv_results = export_csv.export_all(conn)
            for filename, count in csv_results.items():
                print(f"  {filename}: {count} rows")

        if args.export_json:
            print(f"Exporting country-tagged JSON "
                  f"(country: {args.country}, year: {args.year})...")
            stats = export_json.export_all(
                conn, country_code=country_long, year=args.year
            )
            print(f"\n  Main file: {stats['main_count']} region-records")
            for lvl, cnt in stats.get("level_counts", {}).items():
                print(f"  Level {lvl}: {cnt} region-records")
            print(f"  Levels in data: {stats['levels_available']}")

            # Validate the main country-year JSON
            short = config.country_short(country_long)
            main_path = config.json_country_year_path(short, args.year)
            print("\nValidating JSON output...")
            errors = validate.validate_json(main_path)
            if errors:
                print("  VALIDATION ERRORS:")
                for e in errors:
                    print(f"    - {e}")
            else:
                print("  JSON validation passed")

        if not args.skip_jsonp:
            print(f"\nExporting JSONP "
                  f"(countries: {', '.join(export_countries)})...")
            record_count = export_jsonp.export_jsonp(conn, export_countries)
            print(f"  {config.JSONP_PATH.name}: {record_count} records")

            print(f"\nExporting split files (meta.js + per-region)...")
            split_stats = export_split.export_split(conn, export_countries)
            print(f"  meta.js: {split_stats['occ_count']} occupations")
            print(f"  regions/: {split_stats['region_count']} files")

            # Validate JSONP output
            print("\nValidating JSONP output...")
            errors = validate.validate_jsonp()
            if errors:
                print("  VALIDATION ERRORS:")
                for e in errors:
                    print(f"    - {e}")
                sys.exit(1)
            else:
                print("  JSONP validation passed")

        print("\nPipeline complete!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
