# Architecture

## Data Flow
```
BLS2 Pipeline (../bls2/)
  → job_data.js (JSONP) or bls.db (SQLite)
  → scripts/generate-static-data.py
  → public/data/bls-data.json
  → StaticDataProvider (React Context)
  → Adapter hooks (same shapes as original GraphQL hooks)
  → react-canvas-treemap + other viz components
```

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

## Component Modification Strategy
- Minimize changes to react-canvas-treemap calls
- Adapter hooks absorb all data shape translation
- Downstream components see same interfaces
- Only change: cityId:number → regionId:string, route paths, UI labels

## Files Disabled in Phase 1
- Industry Space (network graph)
- Growth Opportunities (PSWOT)
- Similar Cities
- Mapbox map
- Sentry, Google Analytics, Typeform survey
