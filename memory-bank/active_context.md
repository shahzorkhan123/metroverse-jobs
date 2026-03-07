# Active Context

## Current Focus
India PLFS data pipeline complete. Frontend fully working for both US and India.

## What Was Done (2026-02-24, Session 8)

### India District Output Restriction (Population-Based)
1. **`scripts/pipeline/import_plfs.py`**:
   - Replaced city/district occupation-cell suppression (`min_obs_city`) with district population ranking.
   - District population proxy is computed from normalized PLFS person weights.
   - City-level output now keeps only the top configured districts by population.
2. **`scripts/pipeline/config.py`**:
   - Added India config defaults: `district_top_n: 400`, `district_population_min: 0`.
3. **`tests/test_pipeline.py`**:
   - Added regression test `test_city_output_is_limited_to_top_population_districts`.
4. **Verification**:
   - Rebuilt India pipeline and confirmed output now has exactly `400` Metro (district) regions.

## What Was Done (2026-02-24, Session 9)

### India Full Level Coverage + 1M District Population Filter
1. **`scripts/pipeline/config.py`**:
   - Updated India subnational levels to include all available levels: `state_levels: [1,2,3]`, `city_levels: [1,2,3]`.
   - Switched district filter policy from top-N to population-only: `district_top_n: 0`, `district_population_min: 1_000_000`.
2. **`scripts/pipeline/import_plfs.py`**:
   - Added optional per-call overrides: `district_top_n`, `district_population_min` for testing/tuning.
3. **`tests/test_pipeline.py`**:
   - Updated India importer tests to disable population filtering on tiny synthetic fixtures.
4. **Verification**:
   - Rebuilt India outputs successfully with new level structure and filter.
   - Confirmed metro/state level-3 exports are generated (`bls-data-in-2024-3-metro.json`).

## What Was Done (2026-02-24, Session 10)

### City Overview Population + Static Location Graphic
1. **Overview widgets populated from static region data**:
   - Replaced legacy peer-group/population/ranking dependencies in overview widgets with direct metrics from `regionData`.
   - Added workers, annual wage, estimated income, occupation coverage, and top occupations lists for both US and India.
2. **Static location panel**:
   - Replaced map placeholder with a static world-locator graphic using country centroid markers (`us`, `in`).
   - Keeps static-host compatibility (no Mapbox/backend dependency).
3. **Sanity checks**:
   - TypeScript file-level checks pass for modified overview components.
   - Full production build blocked by environment Node/OpenSSL mismatch (`ERR_OSSL_EVP_UNSUPPORTED` with Node 24 + CRA3/Webpack4).

## What Was Done (2026-02-24, Session 6)

### India State + City-Level PLFS Importer
1. **`scripts/pipeline/import_plfs.py`**: Added weighted microdata aggregation pipeline:
   - New `import_india_subnational_from_microdata()` for state + optional city ingestion
   - Auto-detects columns for state, city/district, occupation code, wage, and survey weight
   - Normalizes NCO codes and rolls up to configurable levels (state default: 1-2, city default: 1)
   - Applies suppression thresholds (`min_obs_state`, `min_obs_city`) and computes weighted monthly wages
   - Inserts region-level occupation records compatible with existing export pipeline
2. **National importer preserved**: `import_india_national()` (Table 25 + Table 50) remains unchanged in behavior.
3. **`import_all_india()`** now combines:
   - National published-table import (if files exist)
   - Subnational microdata import (if microdata CSV exists)
   - Complexity recomputation after import
4. **`scripts/pipeline/config.py`**: Added India microdata config keys:
   - `plfs_micro_csv`, `state_levels`, `city_levels`, `min_obs_state`, `min_obs_city`
5. **`scripts/pipeline/run_pipeline.py`**: India country detection now uses normalized `country_long == "IND"` (supports `--country in` and `--country ind`).
6. **`tests/test_pipeline.py`**: Added `TestIndiaPlfsImport` validating weighted state/city aggregation and NCO rollups from synthetic microdata.
7. **Validation**: Full pipeline tests pass (`49 passed`).

## What Was Done (2026-02-24, Session 7)

### India Export Payload + Naming Cleanup
1. **Restored country picker compatibility**:
   - Fixed `public/data/bls-data.json` shape (includes `yearsByCountry` and `countryMetadata`)
   - Updated `export_json.export_meta()` to merge with existing meta catalog instead of replacing it
2. **Slim level-extension payloads for India**:
   - `export_json._build_static_data()` now supports `slim_occupations=True`
   - India level files (`export_level_file` for `country_code == "IND"`) write occupation code/name mapping under `metadata.occupationMap`
   - India level files now omit `occupations` array entries (empty array) to avoid duplicate code metadata in extension payloads
3. **Frontend merge support for slim payloads**:
   - `src/dataProvider/index.tsx` hydrates missing occupation details from `ext.metadata.occupationMap` during `mergeExtension()`
   - `src/dataProvider/types.ts` adds optional `metadata.occupationMap` typing
4. **India title fallback quality**:
   - Added optional `ind_nco_labels.csv` support (`config.COUNTRIES["IND"]["nco_labels_csv"]`)
   - Fallback labels now use hierarchy-aware names (`Division`, `Sub-Division`, `Group`, `Unit Group`) instead of `NCO xxx`
5. **Validation**:
   - Full test suite passes (`49 passed`)
   - Regenerated India outputs with fresh import from uploaded PLFS microdata zip

## What Was Done (2026-02-22, Session 5)

### India PLFS Data Pipeline
1. **Raw CSV extraction** from PLFS 2023-24 PDF:
   - `data/raw/ind_table25_nco_distribution.csv` — 173 NCO codes (1-3 digit) with % distribution
   - `data/raw/ind_table50_nco_wages.csv` — 9 division wages (monthly, rural+urban persons)

2. **Pipeline updates**:
   - `scripts/pipeline/config.py` — Added `NCO_MAJOR_GROUPS`, `NCO_MAJOR_GROUP_COLORS`, IND country config
   - `scripts/pipeline/import_plfs.py` (NEW) — Converts PLFS % → employment counts, assigns wages, calculates GDP
   - `scripts/pipeline/export_json.py` — Added NCO hierarchy dispatch: `_get_level()`, `_get_parent()`, `_get_major_group_id()`, `_detect_code_system()`
   - `scripts/pipeline/run_pipeline.py` — Routes `--country ind` to PLFS import

3. **Generated data files**:
   - `public/data/bls-data-in-2024.json` — 49 occupations (L1+L2), 1 national region (~27KB)
   - `public/data/bls-data-in-2024-3.json` — 124 occupations (L3 only, ~67KB)

### Frontend Fixes
4. **sectorColorMap → useSectorMap**: Fixed `Cannot find color for top section 6` error by replacing hardcoded `sectorColorMap` with metadata-driven `useSectorMap()` hook in all 8 components that used it.

5. **Landing page redesign**: Removed fullscreen country selector cards. Added inline country `<select>` dropdown on the region search page.

6. **Profile page country switching**: Country dropdown in secondary header now stays on the profile page and navigates to the new country's national region instead of going back to landing.

### Verification
- 48/48 pipeline tests pass
- `npm run build` compiles successfully
- India treemap renders with 9 NCO divisions at L1, drill-down to L2/L3 works
- US data unaffected

## Pending
- India state-level data (requires PLFS microdata processing)
- "city" → "region" text cleanup in UI strings
- Large file sizes (gzip recommended)
- GitHub Actions CI/CD and GitHub Pages deployment

## What Was Done (2026-02-24, Session 8)

### India Metro Label Format
1. Updated district-derived metro naming in `scripts/pipeline/import_plfs.py` to append state names.
2. District code rows now export as `District XX, State Name` when unresolved, and mapped rows as `District Name, State Name`.
3. District-name columns are also normalized to include the state suffix when missing.
4. Re-ran India pipeline export and confirmed metro labels now follow `District, State` format (e.g., `Agra, Uttar Pradesh`).

## What Was Done (2026-02-24, Session 9)

### UI Display Normalization for Metro Names
1. Added display-only formatter in `src/hooks/useGlobalLocationData.ts` to title-case metro region labels.
2. Applied formatter to location search data, so search panel labels render consistently.
3. Applied formatter to `src/components/navigation/secondaryHeader/CitySearch.tsx` option labels and sorting.
4. IDs/routing/data keys are unchanged; only rendered text is normalized.
