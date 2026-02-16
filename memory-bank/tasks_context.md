# Tasks Context

## Active
- Task #6: Fix remaining broken imports in active import chain (~6 files)

## Blocked
- Task #5 (filter controls): Blocked by Task #6 (need clean build first)
- Task #7 (deploy): Blocked by Task #5 and #6

## Completed
- Fork metroverse-front-end → metroverse-jobs
- Clone to D:\Projects\metroverse-jobs
- Clean package.json (removed 11 deps)
- Add ATTRIBUTION.md, LICENSE (CC BY-NC-SA 4.0), README.md
- Create scripts/generate-static-data.py → public/data/bls-data.json
- Create src/dataProvider/ (types.ts, index.tsx)
- Rewrite 5 adapter hooks
- Update src/index.tsx (StaticDataProvider + HashRouter)
- Rewrite CompositionTreeMap.tsx (remove gql)
- Update sectorColorMap (22 SOC entries)
- Rewrite landing page (Mapbox → search panel)
- Remove Phase 2 tabs from profiles
- Stub analytics & tracking
- Create CLAUDE.md + memory-bank

## Key Decisions Made
- Single bls-data.json file (not per-region)
- HashRouter for GitHub Pages
- Keep adapter field names (naicsId, numEmploy, numCompany) to minimize downstream changes
- Replace Mapbox map with react-panel-search dropdown
- cityId changed from number to string (regionId)
- Phase 1 only: Overview, Economic Composition, Good At tabs
