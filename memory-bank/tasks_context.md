# Tasks Context

## Active
- None (all current tasks completed)

## Pending
- "city" → "region" text cleanup
- GitHub Actions CI/CD pipeline
- GitHub Pages deployment
- Large metro files (~17-23MB) — gzip for production
- India state-level data (PLFS microdata processing)

## Completed
### Phase 4: India Subnational Pipeline
- Added weighted PLFS microdata importer for India state-level and optional city-level aggregates
- Added configurable suppression thresholds and level rollups (state 1-2 digit, city 1-digit default)
- Added pipeline/config integration and test coverage (`TestIndiaPlfsImport`)

### Phase 1: Foundation & Core Viz
- Fork metroverse-front-end → metroverse-jobs
- Create scripts/generate-static-data.py → public/data/bls-data.json
- Create src/dataProvider/ (types.ts, index.tsx)
- Rewrite 5 adapter hooks
- Rewrite CompositionTreeMap.tsx (remove gql)
- Update sectorColorMap (22 SOC entries)
- Rewrite landing page (Mapbox → search panel)

### Phase 2: Pipeline & Data
- Pipeline → metroverse-jobs migration (scripts/pipeline/)
- Country-tagged pipeline (--country flag)
- Split data by level (meta catalog + per-level extension files)
- Frontend multi-file loading (lazy-load levels via meta catalog)
- Fetch BLS real data (182K records from OES 2024)

### Phase 3: SOC Hierarchy & Visualization
- SOC 4-level remap, context-aware `_soc_parent()`
- Pipeline synthesis (`_synthesize_missing_levels()`)
- Smart treemap filter (leaf nodes, no double-counting, residuals)
- Treemap drill-down, enhanced tooltips
- Level 3+4 split (nat+state vs metro)
- 48 pipeline tests

### Phase 4: Multi-Country Architecture (Session 5)
- `countryMetadata` in bls-data.json (terminology, levels, majorGroups, regionTypes, hierarchyRules)
- Strategy pattern: SOC2018Strategy / NCO2015Strategy
- Metadata-driven hooks: useTerminology, useSectorMap
- Country selector on landing page
- Country/Year/Region dropdowns on profile page

### Phase 5: India Data Pipeline (Session 6)
- PLFS 2023-24 Table 25 + Table 50 extraction to CSV
- import_plfs.py: India-specific import script
- export_json.py: NCO hierarchy dispatch functions
- Generated bls-data-in-2024.json + bls-data-in-2024-3.json
- Fixed sectorColorMap → useSectorMap in 8 components
- Landing page: country dropdown replaces fullscreen selector
- Profile page: country switch stays on page, navigates to national

## Key Decisions Made
- Country-tagged output: `bls-data-{country}-{year}.json`
- Meta catalog: `bls-data.json` lists datasets and level files
- Main file has levels 1+2, level 3/4 separate
- HashRouter for GitHub Pages
- SOC 4 levels, context-aware parent resolution
- India NCO: 3 levels, national only (states later via microdata)
- All color lookups via useSectorMap() hook, never hardcoded sectorColorMap
