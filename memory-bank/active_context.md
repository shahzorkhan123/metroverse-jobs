# Active Context

## Current Focus
Multi-country metadata architecture implemented. Frontend is now metadata-driven for US and India.

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

### Metadata-Driven Multi-Country Architecture (11-Step Plan)
All steps completed, 0 TypeScript errors, build succeeds, 48 pipeline tests pass.

1. **`public/data/bls-data.json`**: Added `yearsByCountry`, `countryMetadata` with full US (SOC, 22 groups) and India (NCO, 10 divisions) metadata including terminology, levels, majorGroups, regionTypes, hierarchyRules
2. **`src/dataProvider/types.ts`**: Added `CountryMetadata` interface, updated `BLSMetaCatalog` with `yearsByCountry`, `countryMetadata`, `flagEmoji`
3. **`src/dataProvider/index.tsx`**: Added `selectedCountry`, `selectedYear`, `countryMetadata`, `switchCountryYear()` to DataState. URL-based initial country selection. Country-aware `fetchAndMerge`. `maxDigitLevel` computed per country.
4. **`src/utils/occupationHierarchy.ts`** (NEW): Strategy pattern — `SOC2018Strategy` (XX-XXXX format, renumbered code handling) and `NCO2015Strategy` (digit-length levels, substring parent). Factory: `getHierarchyStrategy(name)`.
5. **`src/components/dataViz/treeMap/CompositionTreeMap.tsx`**: Replaced inline `socParent()` with `hierarchyStrategy.getParent()`. Tooltips now use metadata-driven labels (occupationCode, wage, employment, currencySymbol).
6. **`src/pages/landing/index.tsx`**: Country selector cards before region search. Flag emojis, country name, classification system subtitle. Back button to change country. Country-specific quick links.
7. **`src/components/navigation/secondaryHeader/CitySearch.tsx`**: Country dropdown from `meta.countries` (not hardcoded). Year dropdown from `yearsByCountry[selectedCountry]`. Region optgroups from `countryMetadata.regionTypes[].pluralName`. `onCountryChange` calls `switchCountryYear()`.
8. **`src/hooks/useSectorMap.ts`**: Uses `countryMetadata.majorGroups` with names/colors directly. Falls back to SOC `sectorColorMap` + fluent strings.
9. **`src/hooks/useTerminology.ts`** (NEW): Returns `countryMetadata.terminology` or US defaults.
10. **`src/components/dataViz/settings/index.tsx`**: Dynamic digit level buttons from `maxDigitLevel`. Level names from `countryMetadata.levels[n].name`.
11. **`src/components/dataViz/industrySpace/chart/`**: `createChart.ts` accepts `occupationCodeLabel` parameter. `index.tsx` passes label from `countryMetadata.terminology.occupationCode`.

## What Was Done (2026-02-22, Session 4)

### India PLFS Data Research
1. **MoSPI MCP Server Integration**:
   - Configured official MoSPI Statistics MCP server (https://mcp.mospi.gov.in)
   - Tested PLFS API: 8 indicators available (LFPR, WPR, UR, wages, worker distribution)
   - API provides 1-digit NCO only, no occupation×wage cross-tabulations
   - Conclusion: MCP server insufficient for detailed occupation data

2. **PLFS Data Structure Analysis**:
   - **NCO 2015 Hierarchy**: 10 divisions (1-digit), ~30 sub-divisions (2-digit), ~116 groups (3-digit), ~436 unit groups (4-digit)
   - **Published tables**: Table 50 has 1-digit NCO × State wages (validated by MOSPI)
   - **Sample size**: ~100K households, ~418K persons, ~4,000 workers per state average
   - **Survey weights**: `mult` field (10-digit) required for population estimation

3. **Data Availability Assessment**:
   - State level: 1-digit NCO reliable (400 workers/occupation/state), 2-digit feasible (133 workers/occupation/state)
   - National level: 1-digit, 2-digit, 3-digit all reliable
   - 3-digit × State: Too sparse (~35 workers/occupation/state), requires suppression
   - NSS EUS (discontinued 2011), ASI (industry not occupation), DGET (too narrow) - all rejected

4. **Proposed India Structure**:
   ```
   State level:    1-digit NCO (10 divisions) × 37 States/UTs = 370 cells [default]
                   2-digit NCO (~30 sub-divisions) × 37 States/UTs = ~1,110 cells [with suppression]
   National level: 1-digit (10) + 2-digit (~30) + 3-digit (~116) NCO = 156 occupation categories
   ```
   Mirrors BLS OEWS structure (major groups at state, detailed at national)

5. **MCP Servers Configured** (6 total):
   - GitHub (global)
   - MoSPI Statistics (https://mcp.mospi.gov.in)
   - Fetch (web scraping)
   - Sequential Thinking (planning)
   - Memory (persistent context)

6. **Other Datasets Evaluated**:
   - ILOSTAT: 1-digit ISCO-08 only, no wages for India
   - ASI: NIC (industry) not NCO (occupation) - rejected
   - DGET: Vocational training sector only - rejected

## What Was Done (2026-02-22, Session 3)

### Pipeline: Synthesis of Missing SOC Levels
1. **`export_json.py`**: Added `_synthesize_missing_levels()` — bottom-up aggregation
   - BLS doesn't publish level 2 (minor group) for states/metros
   - Synthesis: level 3 from level 4 children, then level 2 from level 3
   - Uses `all_codes` (from all records including national) for parent resolution
   - Called inside `_build_static_data()` before level filtering

2. **Context-aware `_soc_parent()`** (Python + TypeScript):
   - Only 3 SOC codes use renumbered XX-XX00 pattern: `15-1200`, `31-1100`, `51-5100`
   - For level 3 (XX-XXX0): tries XX-XX00 first, falls back to XX-X000
   - Accepts `known_codes` set parameter; without context, defaults to XX-X000 (safe)
   - Fixed critical double-counting bug: aggressive fix created 15 phantom codes, adding 19.35M employees

3. **Level 3 file split** (matching level 4 pattern):
   - `bls-data-us-2024-3.json` — nat+state (3.7MB)
   - `bls-data-us-2024-3-metro.json` — metro only (17MB)
   - Frontend `loadLevel()` generalized to fetch `{level}-metro` for any level

### Frontend: Smart Treemap with Residuals
4. **Residual value computation** in `CompositionTreeMap.tsx`:
   - When parent has children that don't fully cover its employment, parent stays visible with residual = parent_total - children_sum
   - `adjustedValueMap` for consistent tooltip display
   - Uses `.forEach()` on Maps (not `for...of`) to avoid TS downlevelIteration issue

### Verification Results (US National)
- Level 1: 154,187,380 employees
- Level 2: 154,186,320 (diff: -1,060, ~0%)
- Level 3: 154,545,940 (+0.23%)
- Level 4: 147,659,390 (95.8% coverage — BLS suppression)
- Zero overlapping codes between levels
- 48 tests pass

### Pipeline Output (Final)
- `bls-data.json` — meta catalog (lists 3-metro and 4-metro)
- `bls-data-us-2024.json` — 8.0 MB (levels 1+2 with synthesis, 116 occ)
- `bls-data-us-2024-3.json` — 3.7 MB (broad, nat+state)
- `bls-data-us-2024-3-metro.json` — 17 MB (broad, metro)
- `bls-data-us-2024-4.json` — 6.0 MB (detailed, nat+state, 819 occ)
- `bls-data-us-2024-4-metro.json` — 23 MB (detailed, metro, 809 occ)

## What Was Done (2026-02-16, Session 2)
- SOC 4-level remap (was 5 levels)
- Smart treemap filter (no double-counting, hierarchical leaf selection)
- Treemap drill-down (click sector → isolate + increase digit level)
- Enhanced tooltips (employees, share%, avg wage, total income)
- DigitLevel enum 4 values, settings panel, region dropdown reorder
- Level 4 split (nat+state vs metro)
- Data validation (parentCode, completeness check)
- 48 tests passing

## Pending
- India data pipeline: Create fetch/import/export scripts for India PLFS data
- India test data: Generate India JSON data files for the frontend
- Some text still says "city" instead of "region"
- Large file sizes (8MB main, 17+23MB metro) — gzip recommended in production
- GDP/income validation (values shift across levels due to aMean rounding in synthesis)
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
