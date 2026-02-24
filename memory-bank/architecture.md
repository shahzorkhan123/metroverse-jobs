# Architecture

## Data Flow
```
BLS OES ZIP files (bls.gov)
  → XLSX (national, state, MSA, nonmetro)
  → Python pipeline (scripts/pipeline/)
  → SQLite (data/bls.db) — 182K records
  → Synthesis of missing levels
  → JSON split by level + region type
  → public/data/bls-data-*.json
  → StaticDataProvider (React Context)
  → Adapter hooks (same shapes as original GraphQL hooks)
  → react-canvas-treemap + other viz components
```

## Pipeline Architecture (`scripts/pipeline/`)
```
run_pipeline.py --year 2024 --country us --fetch --fresh --validate
  ├── fetch_bls.py     → Download OES ZIP → XLSX (US only)
  ├── import_csv.py    → Parse XLSX → SQLite (bls.db) (US)
  ├── import_plfs.py   → PLFS CSV → SQLite (India)
  ├── export_json.py   → SQLite → split JSON files (SOC + NCO dispatch)
  ├── validate.py      → Parent vs child employment checks
  └── config.py        → Paths, URLs, constants, NCO_MAJOR_GROUPS
```

### India Pipeline
```
run_pipeline.py --year 2024 --country ind --fresh
  → import_plfs.import_all_india()
    → Reads data/raw/ind_table25_nco_distribution.csv (173 NCO codes, % distribution)
    → Reads data/raw/ind_table50_nco_wages.csv (9 division wages)
    → Converts % to employment (× 483M total workers)
    → Assigns wages (L2-3 inherit parent division wage)
    → GDP = employment × monthly_wage × 12
    → Complexity = normalized GDP rank
  → export_json.export_all() with NCO dispatch functions
```

### Key Pipeline Functions (export_json.py)
- `_soc_level(code)` → 1-4 based on SOC pattern
- `_soc_parent(code, known_codes)` → context-aware parent resolution
- `_synthesize_missing_levels(records)` → bottom-up gap filling
- `_build_static_data(records, all_soc_codes)` → JSON structure
- `export_level_file(conn, country, year, level, region_types)` → split files

### SOC Hierarchy (4 Levels)
```
Level 1: XX-0000 (major group, 22 groups)
Level 2: XX-X000 or XX-XX00 (minor group)
Level 3: XX-XXX0 (broad occupation)
Level 4: XX-XXXX (detailed occupation)
```

### Context-Aware Parent Resolution
Only 3 SOC codes use renumbered XX-XX00 minor group pattern:
- `15-1200` (Computer Occupations subgroup)
- `31-1100` (Home Health/Personal Care Aides)
- `51-5100` (Printing Workers)

For level 3 codes (XX-XXX0), parent can be XX-X000 (standard) or XX-XX00 (renumbered).
`_soc_parent()` checks `known_codes` set to determine which pattern exists.
Without context, defaults to XX-X000 (safe).

### Pipeline Synthesis
BLS doesn't publish level 2 (minor group) data for states/metros.
`_synthesize_missing_levels()` aggregates bottom-up:
1. Synthesize level 3 from level 4 children
2. Synthesize level 2 from level 3 children
Uses all national+state+metro codes for parent resolution.

## Output File Architecture
```
public/data/
├── bls-data.json                  → Meta catalog (datasets, levelFiles, countries, countryMetadata)
├── bls-data-us-2024.json          → US Main: levels 1+2 (~8MB with synthesis)
├── bls-data-us-2024-3.json        → US Broad: nat+state (~3.7MB)
├── bls-data-us-2024-3-metro.json  → US Broad: metro only (~17MB)
├── bls-data-us-2024-4.json        → US Detailed: nat+state (~6MB)
├── bls-data-us-2024-4-metro.json  → US Detailed: metro only (~23MB)
├── bls-data-in-2024.json          → India Main: levels 1+2 (~27KB, national only)
└── bls-data-in-2024-3.json        → India L3: national only (~67KB)
```

### Meta Catalog (bls-data.json)
```json
{
  "datasets": [
    {"country":"us","year":2024,"file":"bls-data-us-2024.json","levels":[1,2]},
    {"country":"ind","year":2024,"file":"bls-data-in-2024.json","levels":[1,2]}
  ],
  "levelFiles": {
    "us-2024": {
      "3": "bls-data-us-2024-3.json",
      "4": "bls-data-us-2024-4.json",
      "3-metro": "bls-data-us-2024-3-metro.json",
      "4-metro": "bls-data-us-2024-4-metro.json"
    },
    "ind-2024": {
      "3": "bls-data-in-2024-3.json"
    }
  },
  "countryMetadata": {
    "us": { "classificationSystem": "SOC", "currency": "USD", ... },
    "ind": { "classificationSystem": "NCO", "currency": "INR", ... }
  }
}
```

### JSON Data Shape (per file)
```json
{
  "occupations": [{"socCode","name","level","parentCode","majorGroupId","majorGroupName"}],
  "majorGroups": [{"groupId","name","colorCode"}],
  "regions": [{"regionId","name","regionType"}],
  "regionData": { "regionId": { "year": [{"socCode","totEmp","aMean","gdp","complexity"}] } },
  "aggregates": { "year": {"byOccupation":{}, "minMaxStats":{}} }
}
```

## Frontend Data Loading
```
1. Initial: fetch bls-data.json (meta catalog)
2. Main: fetch bls-data-us-2024.json (levels 1+2)
3. On demand: loadLevel(3) → fetch "3" + "3-metro"
4. On demand: loadLevel(4) → fetch "4" + "4-metro"
5. mergeExtension() adds occupations + regionData additively
```

### Smart Treemap Filter
- Shows leaf nodes only (finest available per SOC branch in current region)
- Walk-up ancestor chain: if parent missing, skip to grandparent
- Residual values: parent_total - children_sum for partial coverage
- No double-counting across levels

## Key Mapping (Metroverse → BLS)
| Metroverse | BLS | Field Name Kept |
|---|---|---|
| cityId (number) | regionId (string) | Changed |
| countryId | regionType | Changed |
| naicsId | socCode | Kept as naicsId in adapter output |
| numEmploy | totEmp | Kept as numEmploy |
| numCompany | gdp | Kept as numCompany |
| yearsEducation | complexity | Kept as yearsEducation |
| hourlyWage | aMean (annual) | Kept as hourlyWage |
| NAICS sector (9) | SOC major group (22) | sectorColorMap expanded |
| Knowledge cluster | SOC major group | Mapped |

## Adapter Hook Strategy
Each hook returns `{ loading, error, data }` matching original shapes:
1. `useGlobalLocationData` — regions as cities, regionTypes as countries
2. `useGlobalIndustriesData` / `useGlobalIndustryMap` — occupations as industries
3. `useGlobalClusterData` — major groups as clusters
4. Economic composition query — regionData[id][year] as city industry year data
5. `useAggregateIndustryMap` — min/max wage/complexity for color scaling
6. `useCurrentBenchmark` — stub (null) for Phase 1

## Files Disabled in Phase 1
- Industry Space (network graph)
- Growth Opportunities (PSWOT)
- Similar Cities
- Mapbox map
- Sentry, Google Analytics, Typeform survey
