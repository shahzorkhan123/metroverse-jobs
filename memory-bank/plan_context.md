# Plan Context

## Phase 1: Static BLS Occupation Visualizer
**Status**: Complete

### Sprint 1: Foundation
- [x] Fork repo, clone to D:\Projects\metroverse-jobs
- [x] Create CLAUDE.md and memory bank
- [x] Clean package.json (remove Apollo, Mapbox, analytics)
- [x] Add LICENSE, ATTRIBUTION.md
- [x] Generate static data JSON from bls2
- [x] Create StaticDataProvider
- [x] Update index.tsx and routes

### Sprint 2: Core Viz
- [x] Replace 5 adapter hooks
- [x] Modify CompositionTreeMap
- [x] Update SOC color map (22 entries)

### Sprint 3: Pages
- [x] Rewrite landing page (search, no map)
- [x] Update profile page tabs (3 tabs)
- [x] Update Fluent strings
- [x] Disable Phase 2 pages

### Sprint 4: Deploy & Rebrand
- [x] HashRouter
- [x] Test all region types
- [x] Rebrand to "Metroverse-Jobs" (logo, favicon, titles)
- [x] Rewrite About (5 sections with attribution)
- [x] Rewrite FAQ (10 Q&As)
- [x] Rewrite Contact (GitHub Issues + disclaimer)
- [x] Update screenshots in README
- [ ] GitHub Actions CI/CD
- [ ] Deploy to GitHub Pages

## Phase 2: Pipeline & Multi-Level Data
**Status**: Complete

### Sprint 5: Pipeline
- [x] Migrate pipeline to metroverse-jobs (scripts/pipeline/)
- [x] Country-tagged output (bls-data-us-2024.json)
- [x] Split data by level (meta catalog + extension files)
- [x] Frontend multi-file loading (lazy-load levels)
- [x] Fetch real BLS data (182K records from OES 2024)

### Sprint 6: SOC Hierarchy & Viz
- [x] SOC 4-level remap (major/minor/broad/detailed)
- [x] `_soc_parent()` context-aware (renumbered minor groups)
- [x] Pipeline synthesis of missing levels
- [x] Smart treemap filter (leaf nodes, residuals, no double-counting)
- [x] Treemap drill-down (click sector → isolate + zoom)
- [x] Enhanced tooltips (employees, share%, avg wage, total income)
- [x] DigitLevel enum (4 values), settings panel (4 buttons)
- [x] Region dropdown (States before Metros)
- [x] Level 3+4 split (nat+state vs metro)
- [x] Data validation (--validate flag, completeness check)
- [x] 48 pipeline tests passing

## Phase 3: Future
- Footer rebranding (Harvard Growth Lab → custom)
- "city" → "region" text cleanup
- GDP/income validation across synthesis levels
- Gzip compression for large metro files
- Multi-year support (2020-2024)
- RCA calculations for occupation specialization
- Industry/Occupation Space network graph
- Growth Opportunities (PSWOT chart)
- Similar Regions comparison
- Multi-country support (ISCO for non-US)
