# CLAUDE.md

## Project Overview

**metroverse-jobs** is a fork of Harvard Growth Lab's [Metroverse](https://github.com/harvard-growth-lab/metroverse-front-end) frontend, adapted to visualize US BLS (Bureau of Labor Statistics) occupation data instead of international city/industry data. The original GraphQL backend is replaced with static JSON data files, enabling $0/month GitHub Pages deployment.

**License**: CC BY-NC-SA 4.0 (same as original Metroverse)

## Architecture

```
Original Metroverse:   React → Apollo Client → GraphQL API → PostgreSQL
metroverse-jobs:       React → StaticDataProvider → /data/bls-data-*.json (split static files)
```

### Data Pipeline
```
BLS OES ZIP files (bls.gov)
  → XLSX (national, state, MSA, nonmetro)
  → Python pipeline (scripts/pipeline/)
  → SQLite (data/bls.db) — 182K records
  → Synthesis of missing intermediate levels
  → JSON split by level + region type
  → public/data/bls-data-*.json
```

Run: `python scripts/pipeline/run_pipeline.py --year 2024 --country us --fetch --fresh --validate`

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
├── dataProvider/          # Static data context (replaces Apollo)
│   ├── types.ts           # TypeScript interfaces for BLS data
│   └── index.tsx          # React Context: meta catalog → main file → lazy-load levels
├── hooks/                 # Adapter hooks (same return shapes as original)
│   ├── useGlobalLocationData.ts    # Returns BLS regions as "cities"
│   ├── useGlobalIndustriesData.ts  # Returns SOC occupations as "industries"
│   ├── useGlobalClusterData.ts     # Returns SOC major groups as "clusters"
│   ├── useAggregateIndustriesData.ts # Returns wage/complexity min/max
│   ├── useLevelLoader.ts           # Watches digit_level query param, triggers loadLevel()
│   └── useCurrentBenchmark.ts      # Stub for Phase 1
├── components/dataViz/
│   ├── treeMap/CompositionTreeMap.tsx  # Smart filter, drill-down, residuals, tooltips
│   └── settings/index.tsx             # VIZ OPTIONS panel (4 digit levels)
├── pages/
│   ├── landing/index.tsx    # Region search (no Mapbox map)
│   └── cities/profiles/     # Region profile (3 tabs: Overview, Composition, Good At)
├── types/graphQL/graphQLTypes.ts  # DigitLevel enum (One=1..Four=4)
├── routing/routes.ts        # /region/:regionId/ routes
├── styling/styleUtils.ts    # 22-entry SOC major group color map
└── contextProviders/        # Fluent i18n strings
public/data/
├── bls-data.json              # Meta catalog (datasets, levelFiles, countries, years)
├── bls-data-us-2024.json      # Levels 1+2 (~8MB with synthesis)
├── bls-data-us-2024-3.json    # Broad: nat+state (~3.7MB)
├── bls-data-us-2024-3-metro.json  # Broad: metro only (~17MB)
├── bls-data-us-2024-4.json    # Detailed: nat+state (~6MB)
└── bls-data-us-2024-4-metro.json  # Detailed: metro only (~23MB)
scripts/pipeline/
├── run_pipeline.py    # Orchestrator (--year, --country, --fetch, --fresh, --validate)
├── fetch_bls.py       # Download OES ZIP → XLSX
├── import_data.py     # Parse XLSX → SQLite
├── export_json.py     # SQLite → split JSON (synthesis, parent resolution, level split)
├── validate.py        # Parent vs child employment checks
└── config.py          # Paths, URLs, constants
tests/
└── test_pipeline.py   # 48 tests (pipeline + export + validation)
```

## SOC Hierarchy (4 Levels)

```
Level 1: XX-0000  (major group, 22 groups)
Level 2: XX-X000 or XX-XX00  (minor group — XX-XX00 is SOC 2018 renumbered)
Level 3: XX-XXX0  (broad occupation)
Level 4: XX-XXXX  (detailed occupation)
```

### Critical: Context-Aware Parent Resolution
Only 3 SOC codes use renumbered XX-XX00 minor group pattern: `15-1200`, `31-1100`, `51-5100`.
For level 3 codes (XX-XXX0), parent can be either:
- XX-X000 (standard) — e.g., 29-1140 → 29-1000
- XX-XX00 (renumbered) — e.g., 15-1210 → 15-1200

`_soc_parent(code, known_codes)` checks `known_codes` set to determine which exists.
Without context, defaults to XX-X000 (safe). Both Python and TypeScript implementations.

### Pipeline Synthesis
BLS doesn't publish level 2 (minor group) for states/metros.
`_synthesize_missing_levels()` aggregates bottom-up:
1. Synthesize level 3 from level 4 children
2. Synthesize level 2 from level 3 children
Uses all codes (including national) for parent resolution.

## Data Loading

```
1. Initial: fetch bls-data.json (meta catalog)
2. Main: fetch bls-data-us-2024.json (levels 1+2)
3. On demand: loadLevel(3) → fetchAndMerge("3") + fetchAndMerge("3-metro")
4. On demand: loadLevel(4) → fetchAndMerge("4") + fetchAndMerge("4-metro")
5. mergeExtension() adds occupations + regionData additively
```

## Smart Treemap Filter

- Shows **leaf nodes only** (finest available per SOC branch in current region)
- Walk-up ancestor chain: if parent missing in data, skip to grandparent
- **Residual values**: parent_total - children_sum for partial coverage (BLS suppression)
- **No double-counting** across levels — verified: US National L1=154.2M, L2=154.2M
- **Drill-down**: click sector → isolate + increase digit level by 1

## Development

```bash
npm install    # Install dependencies (Node 16 recommended)
npm start      # Dev server at localhost:3000
npm run build  # Production build
```

### Pipeline
```bash
# Full pipeline with real BLS data
python scripts/pipeline/run_pipeline.py --year 2024 --country us --fetch --fresh --validate

# Export only (from existing SQLite DB)
python scripts/pipeline/run_pipeline.py --year 2024 --country us --export-only

# Run tests
pytest tests/test_pipeline.py -v  # 48 tests
```

### Key Technical Details
- **React 16** with react-scripts 3.4.3 (CRA)
- **TypeScript** ~3.7 — no `downlevelIteration`, use `.forEach()` on Maps not `for...of`
- **Styled Components** for CSS-in-JS
- **HashRouter** for GitHub Pages SPA compatibility
- **react-canvas-treemap** (MIT) for treemap rendering
- **react-panel-search** for hierarchical region search
- **Fluent** for i18n strings
- **No backend** — pure static site

### Important Constraints
1. Keep `react-canvas-treemap` calls unchanged — only change the data fed to them
2. Adapter hooks must return the **exact same data shapes** as original GraphQL hooks
3. Use field names like `naicsId`, `numEmploy`, `numCompany` in adapter output
4. Node 16 required for build compatibility with react-scripts 3.4.3
5. No `for...of` on `Map.entries()` — use `.forEach()` (TS downlevelIteration not enabled)
6. BLS fetch requires `User-Agent` header or returns 403 Forbidden

## BLS OES Data Format (2024)
- National ZIP: `oesm24nat.zip` → `national_M2024_dl.xlsx`
- State ZIP: `oesm24st.zip` → `state_M2024_dl.xlsx`
- Metro ZIP: `oesm24ma.zip` → `MSA_M2024_dl.xlsx` + `BOS_M2024_dl.xlsx`
- Column `O_GROUP` (NOT `OCC_GROUP`): values = total, major, minor, broad, detailed
- Column `AREA_TYPE`: string "1"=national, "2"=state, "4"=MSA, "6"=nonmetro
- Region_Type: `"Metro"` (NOT `"Metropolitan"`) — matches HTML dropdown and DB

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
- `active_context.md` — Current work focus and session history
- `plan_context.md` — Phase tracking and plan status
- `tasks_context.md` — Active/blocked/completed tasks
- `project_overview.md` — Project description and tech stack
- `requirements.md` — User requirements and constraints
- `architecture.md` — Technical architecture and data flow
- `design_decisions.md` — Key decisions and rationale
- `tasks_todo.md` — Remaining work items
