# Plan Context

## Phase 1: Static BLS Occupation Visualizer
**Status**: Complete (Core functionality + Rebranding)

### Sprint 1: Foundation
- [x] Fork repo
- [x] Clone to D:\Projects\metroverse-jobs
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

## Phase 2: Future
- Task #5: Filter controls & useVizOptions hook
- Task #9: Split data files by digit level (bls-data-us-2024-2.json etc.)
- Detailed SOC data, multi-year, RCA, network graph, PSWOT, similar regions, multi-country
- Footer rebranding (currently still shows Harvard Growth Lab)
