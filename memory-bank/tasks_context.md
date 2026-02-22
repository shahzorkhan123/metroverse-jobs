# Tasks Context

## Active
- None (all current tasks completed)

## Pending
- Footer branding cleanup (Harvard Growth Lab → Metroverse-Jobs)
- "city" → "region" text cleanup
- GitHub Actions CI/CD pipeline
- GitHub Pages deployment
- Large metro files (~17-23MB) — gzip for production
- GDP/income validation across levels (aMean rounding in synthesis)

## Completed
### Phase 1: Foundation & Core Viz
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

### Phase 2: Pipeline & Data
- **Pipeline → metroverse-jobs migration** (scripts/pipeline/)
- **Country-tagged pipeline** (--country flag, bls-data-us-2024.json format)
- **Split data by level** (meta catalog + per-level extension files)
- **Frontend multi-file loading** (lazy-load levels via meta catalog)
- **Fetch BLS real data** (182K records from OES 2024: nat + 51 states + 380 metros)

### Phase 3: SOC Hierarchy & Visualization
- **SOC 4-level remap** (major/minor/broad/detailed)
- **`_soc_parent()` context-aware** (handles 3 renumbered XX-XX00 codes)
- **`parentCode` field** in occupations array
- **Pipeline synthesis** (`_synthesize_missing_levels()` — fills state/metro gaps)
- **Smart treemap filter** (leaf nodes only, no double-counting)
- **Residual value computation** (parent shows uncovered employment)
- **Treemap drill-down** (click sector → isolate + increase digit level)
- **Enhanced tooltips** (employees, share%, avg wage, total income)
- **DigitLevel enum** (4 values: One, Two, Three, Four)
- **Settings panel** (4 digit level buttons with labels)
- **Region dropdown** (States before Metropolitan Areas)
- **Level 3+4 split** (nat+state vs metro files, lazy-loaded)
- **Level 3 metro split** (bls-data-us-2024-3-metro.json)
- **Data validation** (completeness check, --validate flag)
- **48 pipeline tests** all passing

## Key Decisions Made
- Country-tagged output: `bls-data-{country}-{year}.json` naming convention
- Meta catalog: `bls-data.json` lists available datasets and level files
- Main file has levels 1+2, level 3/4 are separate extension files
- Levels 3+4 split into nat+state (small) and metro (large) for lazy loading
- Frontend merges extensions additively (no full re-download)
- HashRouter for GitHub Pages
- Keep adapter field names (naicsId, numEmploy, numCompany) to minimize changes
- SOC 4 levels: XX-0000=1, XX-X000/XX-XX00=2, XX-XXX0=3, XX-XXXX=4
- Context-aware `_soc_parent()`: check known_codes for renumbered minor groups
- Pipeline synthesis fills missing intermediate levels bottom-up
- Smart treemap filter shows leaf nodes only (finest available per SOC branch)
- Residual values preserve uncovered employment in parents
- Drill-down click isolates parent sector and increases digit level by 1
