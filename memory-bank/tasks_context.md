# Tasks Context

## Active
- None (all current tasks completed)

## Pending
- Build and verify frontend treemaps with real multi-level data
- Footer branding cleanup (Harvard Growth Lab → Metroverse-Jobs)
- 23MB metro detailed file — consider gzip for production

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
- **Pipeline → metroverse-jobs migration** (32 tests pass)
- **Country-tagged pipeline** (--country flag, bls-data-us-2024.json format)
- **Split data by level** (meta catalog + per-level extension files)
- **Frontend multi-file loading** (lazy-load levels 3-5)
- **Fetch BLS real data** (182K records from OES 2024: national + 51 states + 380 metros)
- **SOC 4-level remap** (was 5, now: major/minor/broad/detailed)
- **Smart treemap filter** (no double-counting, hierarchical leaf selection)
- **Treemap drill-down** (click sector → isolate + increase digit level)
- **Enhanced tooltips** (always show employees, share%, avg wage, total income)
- **DigitLevel enum** (4 values: One, Two, Three, Four)
- **Region dropdown** (States before Metropolitan Areas)
- **Level 4 split** (nat+state vs metro files, lazy-loaded)
- **Data validation** (parentCode in occupations, completeness check)
- **48 pipeline tests** all passing

## Key Decisions Made
- Country-tagged output: `bls-data-{country}-{year}.json` naming convention
- Meta catalog: `bls-data.json` lists available datasets and level files
- Main file has levels 1+2, level 3/4 are separate extension files
- Level 4 split into nat+state (6MB) and metro (23MB) for lazy loading
- Frontend merges extensions additively (no full re-download)
- HashRouter for GitHub Pages
- Keep adapter field names (naicsId, numEmploy, numCompany) to minimize downstream changes
- BLS fetch includes all SOC levels (major/minor/broad/detailed), not just detailed
- SOC 4 levels: XX-0000=1, XX-X000/XX-XX00=2, XX-XXX0=3, XX-XXXX=4
- Smart treemap filter shows leaf nodes only (finest available per SOC branch)
- Drill-down click isolates parent sector and increases digit level by 1
