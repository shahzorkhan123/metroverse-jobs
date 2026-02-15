# CLAUDE.md

## Project Overview

**metroverse-jobs** is a fork of Harvard Growth Lab's [Metroverse](https://github.com/harvard-growth-lab/metroverse-front-end) frontend, adapted to visualize US BLS (Bureau of Labor Statistics) occupation data instead of international city/industry data. The original GraphQL backend is replaced with static JSON data files, enabling $0/month GitHub Pages deployment.

**License**: CC BY-NC-SA 4.0 (same as original Metroverse)

## Architecture

```
Original Metroverse:   React → Apollo Client → GraphQL API → PostgreSQL
metroverse-jobs:       React → StaticDataProvider → /data/bls-data.json (static file)
```

### Key Mapping (Metroverse → BLS)
| Metroverse Concept | BLS Equivalent |
|---|---|
| City | Region (National/State/Metro) |
| Country | Region Type |
| NAICS Industry | SOC Occupation |
| NAICS Sector (9) | SOC Major Group (22) |
| Knowledge Cluster | SOC Major Group |
| Establishments | GDP (TOT_EMP × A_MEAN) |
| Education | Complexity Score |

### Directory Structure
```
src/
├── dataProvider/          # NEW: Static data context (replaces Apollo)
│   ├── types.ts           # TypeScript interfaces for BLS data
│   └── index.tsx          # React Context fetching bls-data.json
├── hooks/                 # Adapter hooks (same return shapes as original)
│   ├── useGlobalLocationData.ts    # Returns BLS regions as "cities"
│   ├── useGlobalIndustriesData.ts  # Returns SOC occupations as "industries"
│   ├── useGlobalClusterData.ts     # Returns SOC major groups as "clusters"
│   ├── useAggregateIndustriesData.ts # Returns wage/complexity min/max
│   ├── useVizOptions.ts            # NEW: URL query param filter state
│   └── useCurrentBenchmark.ts      # Stub for Phase 1
├── components/dataViz/
│   ├── treeMap/CompositionTreeMap.tsx  # Uses adapter hooks instead of gql
│   └── settings/index.tsx             # VIZ OPTIONS panel (adapted)
├── pages/
│   ├── landing/index.tsx    # Region search (no Mapbox map)
│   └── cities/profiles/     # Region profile (3 tabs: Overview, Composition, Good At)
├── routing/routes.ts        # /region/:regionId/ routes
├── styling/styleUtils.ts    # 22-entry SOC major group color map
└── contextProviders/        # Fluent i18n strings
public/
└── data/
    └── bls-data.json        # Generated static data file
scripts/
└── generate-static-data.py  # Reads from ../bls2/ and outputs bls-data.json
```

## Data

### BLS Data Schema (in bls-data.json)
- `regions[]` — National, State, Metro regions with unique regionId
- `occupations[]` — SOC codes with major group mapping
- `majorGroups[]` — 22 SOC major groups with colors
- `regionData[regionId][year][]` — Employment, wage, GDP, complexity per occupation
- `aggregates[year]` — Min/max stats for color scaling

### Data Source
- Generated from `../bls2/data/job_data.js` (JSONP) or `../bls2/data/bls.db` (SQLite)
- Run: `python scripts/generate-static-data.py`

## Development

```bash
npm install    # Install dependencies (Node 16 recommended)
npm start      # Dev server at localhost:3000
npm run build  # Production build
```

### Key Technical Details
- **React 16** with react-scripts 3.4.3 (CRA)
- **TypeScript** ~3.7
- **Styled Components** for CSS-in-JS
- **HashRouter** for GitHub Pages SPA compatibility
- **react-canvas-treemap** (MIT) for treemap rendering — this is the core viz component
- **react-panel-search** for hierarchical region search
- **Fluent** for i18n strings
- **No backend** — pure static site

### Important Constraints
1. Keep `react-canvas-treemap` calls unchanged — only change the data fed to them
2. Adapter hooks must return the **exact same data shapes** as original GraphQL hooks
3. Use field names like `naicsId`, `numEmploy`, `numCompany` in adapter output to minimize downstream changes
4. Node 16 required for build compatibility with react-scripts 3.4.3
5. No Mapbox token needed (map removed in Phase 1)

## Filter Controls
- **Top bar**: Year, Region Type, Region dropdowns
- **VIZ OPTIONS panel**: Size by, Color by, Aggregation, Occupation Limit
- All filters encoded in URL query params for shareable links
- Pattern: `/region/state-california/economic-composition?year=2024&color_by=wage`

## Deployment
- GitHub Pages via GitHub Actions
- `"homepage": "https://shahzorkhan123.github.io/metroverse-jobs"`
- HashRouter for SPA routing on static hosting

## Attribution
- Footer: "Based on Metroverse by Harvard Growth Lab. Licensed under CC BY-NC-SA 4.0."
- `ATTRIBUTION.md`: Full credit with links

## Token Optimization & Memory Bank
1. **Read `memory-bank/` files** at start of each task — only load relevant files
2. **Never rely on chat history** for project context — load from memory-bank
3. **Keep memory-bank files updated** after completing work
4. **Keep responses short** unless detail is requested

### Memory Bank Files
- `active_context.md` — Current work focus and next steps
- `plan_context.md` — Phase tracking and plan status
- `tasks_context.md` — Active/blocked/completed tasks
- `project_overview.md` — Project description and tech stack
- `requirements.md` — User requirements and constraints
- `architecture.md` — Technical architecture and data flow
- `design_decisions.md` — Key decisions and rationale
- `tasks_todo.md` — Remaining work items
