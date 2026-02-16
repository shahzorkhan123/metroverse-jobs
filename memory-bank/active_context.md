# Active Context

## Current Focus
COUNTRY-TAGGED PIPELINE + SPLIT DATA + FRONTEND LOADING complete.

## What Was Done (2026-02-16)

### Pipeline Changes
1. **`.gitignore`**: Removed pipeline artifact ignores (bls.db, export/, raw/). Only `data/raw/*.xlsx` is ignored.
2. **`config.py`**: Added `country_short()` helper, `json_country_year_path()`, `json_country_year_level_path()`, `json_meta_path()`.
3. **`export_json.py`**: Rewritten for country-tagged output:
   - `export_country_year()` → `bls-data-us-2024.json` (levels 1+2)
   - `export_level_file()` → `bls-data-us-2024-{3,4,5}.json` (single level extension)
   - `export_meta()` → `bls-data.json` (catalog of available datasets)
   - `export_all()` → convenience function that produces all files
   - Legacy `export_json()` and `export_json_levels()` preserved for backward compat
4. **`run_pipeline.py`**: Added `--country` flag (default: "us"), wired to `export_all()`
5. **`fetch_bls.py`**: Fixed multiple issues:
   - Column name: `O_GROUP` (not `OCC_GROUP`)
   - Filter: now includes all OCC groups (major, minor, broad, detailed) not just "detailed"
   - Metro: prefers `MSA_M2024_dl.xlsx` over BOS nonmetropolitan file
   - AREA_TYPE: handles string values ("3" or "4")
   - Added User-Agent header to avoid 403 errors

### Frontend Changes
6. **`src/dataProvider/types.ts`**: Added `BLSMetaCatalog` interface for meta file, extended `BLSData.metadata` with optional `country`, `maxLevel`, `level`.
7. **`src/dataProvider/index.tsx`**: Rewritten for multi-file loading:
   - Fetches meta catalog first, then main country-year file (levels 1+2)
   - `loadLevel(level)` function for lazy-loading level extensions (3, 4, 5)
   - `mergeExtension()` merges occupation + regionData + aggregates additively
   - Cached per level (no re-fetch on repeated selections)
   - Context exposes: `data`, `loading`, `error`, `loadedLevels`, `loadLevel`, `levelLoading`, `meta`
8. **`src/hooks/useLevelLoader.ts`**: New hook that watches `digit_level` query param and triggers `loadLevel()` for levels 3+
9. **Added `useLevelLoader()` to**: `cityComposition/index.tsx`, `goodAt/index.tsx`

### Tests
10. **`tests/test_pipeline.py`**: 44 tests (was 32), added:
    - `TestConfig`: `test_country_short`, `test_json_country_year_path`, `test_json_country_year_level_path`, `test_json_meta_path`
    - `TestExportCountryTagged`: 5 tests (country_year, level_file, empty_level, meta, export_all)
    - `TestExactLevelFilter`: 2 tests (exact_level_5, exact_level_1)
    - `TestValidateJson.test_validate_country_year_json`
    - Updated seeded_db fixture with multi-level occupations (7 occs instead of 5)

### Pipeline Output (Real Data)
- **182,187 records** from BLS OES 2024:
  - National: 1,388 records, 113 level 1+2 occupations
  - States: 35,606 records
  - Metros: 145,186 records (380+ MSAs)
- **Output files**:
  - `bls-data.json` (meta catalog)
  - `bls-data-us-2024.json` — 1.8 MB (levels 1+2)
  - `bls-data-us-2024-3.json` — 2.6 KB
  - `bls-data-us-2024-4.json` — 721 KB
  - `bls-data-us-2024-5.json` — 29 MB

## Pending
- Build frontend and verify treemaps render with real data
- Level 5 file (29MB) may need compression or further splitting
- Footer still shows Harvard Growth Lab branding
- Some text still says "city" instead of "region"
