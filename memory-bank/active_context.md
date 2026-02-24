# Active Context

## Current Focus
India PLFS data pipeline complete. Frontend fully working for both US and India.

## What Was Done (2026-02-23, Session 6)

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
- Multi-year support
