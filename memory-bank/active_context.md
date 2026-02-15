# Active Context

## Current Focus
Setting up the forked repo and beginning Phase 1 implementation.

## Recently Completed
- Forked harvard-growth-lab/metroverse-front-end → shahzorkhan123/metroverse-jobs
- Cloned to D:\Projects\metroverse-jobs
- Explored full codebase structure
- Created CLAUDE.md and memory-bank

## In Progress
- Clean package.json (remove Apollo, Mapbox, analytics deps)
- Add LICENSE, ATTRIBUTION.md

## Next Steps
1. Clean package.json dependencies
2. Create data generation script (scripts/generate-static-data.py)
3. Create StaticDataProvider and adapter hooks
4. Modify routing, treemap, colors, strings
5. Build and deploy config

## Key Files to Modify
- `src/index.tsx` — Remove Apollo, add StaticDataProvider
- `src/routing/routes.ts` — city → region routes
- `src/hooks/*.ts` — All adapter hooks
- `src/components/dataViz/treeMap/CompositionTreeMap.tsx` — Remove gql, use adapter
- `src/components/dataViz/settings/index.tsx` — Update labels
- `src/pages/landing/index.tsx` — Replace map with search
- `src/styling/styleUtils.ts` — 22-entry SOC color map
