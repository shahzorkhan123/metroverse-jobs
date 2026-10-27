# Active Context

## Current Focus (2026-10-25, later session): Occupation Space + Job Space — UNCOMMITTED
User asked: nothing committed/staged; they review first. Built & tested locally (24/24 Playwright, 52+9 pytest).
- Pipeline: `scripts/pipeline/compute_space.py` (RCA, φ, ECI/PCI, wage-seeded JCI/TCI, backbone,
  layout, Louvain, hulls, apply PCI to data files, register `spaceFiles` in bls-data.json).
  Run: `python scripts/pipeline/run_pipeline.py --year 2024 --country us --space-only` (~60s).
  `fetch_onet.py` rewritten (writes data/raw/onet_job_dwa.csv; old broken JCI removed).
- Outputs: public/data/space-us-2024-{occupation,job}.json, complexity-us-2024.json; `complexity`
  field in all bls-data-us-2024*.json now PCI-based.
- Frontend: tab "Occupation Space" (route /city/:id/occupation-space, `?space=job`), US only;
  hooks/useSpaceData.ts; useLayoutData/useRCAData rewritten (real RCA, string region ids);
  createChart: backbone links, PCI/JCI colours, zoom labels; sideNav fix for shrinking tab list.
- Notebooks: notebooks/space-playground (exploration knobs), notebooks/task-complexity-analysis
  (article → public/analysis/task-complexity-analysis/*.html, card on Analysis page, Colab badge
  works once pushed).
- Open questions for user: JCI n=20 oversmooths (task-family bands); PCI vs JCI ρ=0.05.

## Current Focus (2026-10-25, end of session)
India PLFS weight/earnings fix is **done, committed and pushed to master** (`b104d7f`, `fb6d30f`,
`0712de8`, `3192322`; also on branch `india-plfs-weights-fix`). "Deploy to GitHub Pages" workflow
succeeded; "pages build and deployment" was still running at session end and the live site still
served old data (372.4M workers, no usdExchangeRates). **First thing next session**: confirm the live
India overview shows "₹165,141 (≈ $1,987 USD)" / "₹86.8 trillion (≈ $1.04 trillion USD)".
Next session starts a different part of the project.

### Open items carried forward
- Push auth: Windows Credential Manager holds an expired GitHub token; `gh` is logged in (repo scope).
  Pushed via `git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push`.
  Permanent fix: `gh auth setup-git` (not configured yet as of session end).
- PLFS time series national line = ILOSTAT total (583M, 2024) × MoSPI %, but states sum to PLFS 526M.
- 2024 wages still below Table 50 for Managers (₹35.5k vs ₹43.0k) and Crafts (₹12.4k vs ₹15.4k).
- Unpaid helpers (status 21) get occupation avg wage in gdp = emp × aMean → slight overstatement.
- `public/serve.json` is unused (Playwright uses `tests/playwright/serve-build.js`); safe to delete.
- Pending feature TODOs unchanged: Time Series CSV/PNG download, treemap CSV download.

### Session transcripts
Old Claude Code transcripts were deleted by auto-cleanup (`cleanupPeriodDays`, ran 2026-10-24); only
prompt history survives in `~/.claude/history.jsonl`. `winfr /extensive` recovered nothing useful
(2 jar fragments); `/regular` mode not yet tried. Consider `"cleanupPeriodDays": 99999` in
`~/.claude/settings.json` (not set). History below reconstructed from prompt history + git.

## Session History Reconstructed (2026-03-08 → 2026-05-04)
- **03-08**: Time series (BLS OES / ILOSTAT / PLFS), GDP spot-check of Management vs PDF.
- **04-03 → 04-11**: State Distribution treemap (national only); state abbreviations moved into
  `bls-data.json` countryMetadata; fixed freeze when switching away from State Distribution
  (ref-gate on `setIndicatorContent`); Playwright MCP installed; `tests/playwright/pre-checkin.spec.ts` added.
- **04-11 → 04-12**: India state comparative analysis — `data/analysis.db` + Jupyter notebook in
  `notebooks/india-state-analysis/` (Colab-editable, collapsible Reproducibility section);
  Analysis tab added before About, linking `public/analysis/india-state-analysis/`.
  2018 vs 2024 state composition chart; ILOSTAT absolute employment chart.
- **04-12 → 04-26**: Removed synthetic state data. User downloaded PLFS microdata (Stata .dta,
  2017-18 → 2023-24) into `data/raw/plfs_microdata/`; per-year district code files added.
  City/district time series discussed (population-threshold districts).
- **04-29 → 05-03**: Fixed timeseries metadata regression (empty India time series);
  real PLFS state time series; JSON pretty-print step in export; notebook rerun.
  Lakshadweep "all agriculture in 2018" issue → changed to filtering at state/city level
  (honor all NCO values if the region has enough sample) + data-quality disclaimer.
  Fixed Analysis "Read article" link rendering root. Committed + pushed (`bb3c97c`, deployed 05-04).
- **05-04 (uncommitted)**: 3rd chart = % change per NCO 2018→2024 (red/green, labels top+bottom);
  merge "&" duplicates (Andaman & Nicobar, Jammu & Kashmir) and fold Daman & Diu / Dadra & Nagar
  Haveli into "Dadra and Nagar Haveli and Daman and Diu"; also needed in region dropdown JSON.

## Uncommitted Work (git, as of 2026-10-25 start of session — ALL NOW COMMITTED, see Current Focus)
- Staged: `scripts/rebuild_analysis_db.py` (`normalise_region()` alias maps), notebook `.py/.ipynb/.html`,
  figures, `data/analysis.db.gz`, `public/analysis/...html`.
- Unstaged: `scripts/pipeline/export_json.py` (`_make_region_id` turns "&" → "and" before slugging),
  regenerated `public/data/bls-data-in-{2018..2024}{,-3}.json` (duplicate "&" regions removed),
  further notebook/figure edits.
- ⚠️ **Confirmed bug — do not commit the regenerated JSON as-is**: merging "&"/"and" aliases SUMS the
  duplicate regions instead of keeping one. 2024 L1 employment HEAD → working tree:
  J&K 3,277,772 → 6,555,544 (exactly 2×); Andaman 131,064 (+126,838 "&" copy) → 257,902;
  DNH&DD 260,971 (+236,381 "Daman & Diu") → 497,352. National unchanged (372.4M) so state totals
  no longer reconcile. Fix: on alias collision keep the canonical record (drop the alias), don't add.
- Untracked junk: `nul`, `dev-server.log`, `test-results/`.

## Overview Wage Currency Bug (fixed 2026-10-25, not yet deployed)
- Hosted site showed India "Annual Mean Wage **$165,302**". The value is correct in INR
  (₹1.65 lakh/yr = national GDP ÷ workers, same in HEAD and hosted JSON); only the symbol was wrong.
- Cause: `overview/widgets/topRow/index.tsx` hardcoded `$` (since `83f2d4e`, 2026-02-24).
- Fix: use `countryMetadata.currencySymbol` (same pattern as treemap tooltips) for wage + Estimated Income.
- Remaining nuance: avg wage = Σgdp / Σemp includes occupations with `aMean = 0` (suppressed wages)
  in the denominator → understates wage in small states (e.g. Andaman occ 4). Consider excluding them.

## PLFS Weight/Earnings Fix (2026-10-25, DONE — committed + pushed)
Spot-check vs PLFS showed labour income ₹61.6T ≈ 21% of GDP (too low). Root causes found in
`scripts/pipeline/convert_dta_all_years.py`:
1. Weight was `mult/1000` → official annual rule `mult/(no_qtr×100)` if NSS==NSC else `/(no_qtr×200)`.
   Now reproduces published WPR (PS+SS) every year (2017-18 34.7% … 2023-24 43.7%).
2. Earnings used `b6q10` = **self-employed only**. Now: regular `b6q9` → self-employed `b6q10`
   → casual 7-day wages (`^b6q9_.*3pt[1-7]`, 14 cols) × 30.4/7. All monthly; importer ×12.
3. Workers were principal-status only → now PS+SS (subsidiary NCO `b5pt2q6` for SS-only workers).
   2024: 372M → 526M workers.
4. District col `distcode_perv1` (2021-24) was never matched → added. District filter stays
   **workers-only ≥1M** (user: small metro output is intentional; 2018 ~100 metros OK).
5. 2018-19 CSV now goes through the same `frame_to_csv()` (pandas) as the .dta files.
6. `import_plfs.import_all_india()` now DELETEs that year's IND rows first → fixes "&"/"and"
   duplicate regions being summed at export (J&K 2×, Andaman, DNH&DD).
Frontend (`overview/widgets/topRow/index.tsx`, `dataProvider/types.ts`):
- Currency symbol from `countryMetadata.currencySymbol` (was hardcoded `$`).
- "Estimated Income" → "Estimated Labour Income" + tooltip (not GDP).
- USD equivalent shown when `countryMetadata.usdExchangeRates[year]` exists (type added).

### Checklist (completed)
- [x] Re-run of all years completed + verified (2026-10-25). No "&" regions; states sum = national (1.000).
      | yr | workers | wage/mo | labour income | metros |
      | 2018 | 372.6M | ₹10,059 | ₹45.0T | 100 |  | 2019 | 380.5M | ₹10,763 | ₹49.1T | 104 |
      | 2020 | 423.2M | ₹11,004 | ₹55.9T | 120 |  | 2021 | 437.5M | ₹11,154 | ₹58.6T | 128 |
      | 2022 | 459.1M | ₹12,284 | ₹67.7T | 141 |  | 2023 | 502.7M | ₹13,339 | ₹80.5T | 160 |
      | 2024 | 525.8M | ₹13,762 | ₹86.8T | 168 |  (was 372.4M / ₹13,775 / ₹61.6T)
      2024 per-division wages now ≈ Table 50 (e.g. Technicians 24,185 vs 24,199; Clerical 23,339 vs 23,616);
      Managers 35,477 vs 42,993 and Crafts 12,419 vs 15,350 still low — minor follow-up.
- [x] `usdExchangeRates` in `bls-data.json` → `countryMetadata.in`: RBI Handbook Table 132 calendar-year
      averages, PLFS year Y = mean(CY Y-1, CY Y): 2018 66.76 … 2024 83.13. Overview: ₹165,141 (≈ $1,987),
      ₹86.8T (≈ $1.04T).
- [x] PLFS time series rebuilt. Note: national line = ILOSTAT total (583M 2024) × MoSPI %, states sum to
      PLFS 526M — pre-existing design mismatch, not fixed.
- [x] analysis.db rebuilt with **`--lite`** (4.5MB gz; full build is 17MB — May-4 commit used lite).
      Notebook executed in place (.ipynb, not regenerated from .py), HTML + figures copied to public/analysis.
- [x] Stale `bls-data-in-2024-3-metro.json` removed (city_levels=[1] since 4f450a2) + catalog entry;
      `export_meta` now rebuilds each exported country-year's `levelFiles` entry.
- [x] pytest 52/52 (fixed pre-existing failing `test_subsample_multiplier_is_scaled` fixture; added
      `TestPlfsMicrodataConversion`). Build OK. Playwright 17/17 (+2 overview currency tests).
- Playwright webServer: `npx serve` + `public/serve.json` rewrites never worked (`/$1` literal, `:path*`
      encodes `/`); May-3 passes reused a dev server. Replaced with `tests/playwright/serve-build.js`.
      `public/serve.json` is now unused.
- [x] Committed (3 commits + .gitignore) and pushed to master 2026-10-25.
- Caveat: unpaid helpers (status 21) get the occupation avg wage in gdp = emp × aMean → slight overstatement.
- Backup of pre-fix data: scratchpad `backup/` (bls-data*.json, bls.db) — session temp, may vanish.

## Previous Focus
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
