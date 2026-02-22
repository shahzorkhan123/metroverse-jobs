# Active Context

## Current Focus
SOC 4-level hierarchy, smart treemap, drill-down, enhanced tooltips — all complete.

## What Was Done (2026-02-16, Session 2)

### Pipeline: 4-Level SOC Remap
1. **`export_json.py`**: `_soc_level()` remapped from 5 levels to 4:
   - Level 1: XX-0000 (major), Level 2: XX-X000 or XX-XX00 (minor), Level 3: XX-XXX0 (broad), Level 4: XX-XXXX (detailed)
   - Added `_soc_parent()` for hierarchy traversal
   - Added `parentCode` field to occupations array
   - Added `region_types` filter to `export_level_file()`
   - Level 4 split: nat+state file + metro-only file (`4-metro`)
2. **`config.py`**: `json_country_year_level_path()` accepts `int | str` for "4-metro"
3. **`validate.py`**: Added `validate_completeness()` — compares parent employment vs child sums
4. **`run_pipeline.py`**: Added `--validate` flag
5. **48 tests pass** (was 44)

### Frontend Changes
6. **`graphQLTypes.ts`**: `DigitLevel` enum → 4 values (One=1, Two=2, Three=3, Four=4)
7. **`settings/index.tsx`**: 4 digit level buttons with descriptive labels
8. **All DigitLevel.Six → DigitLevel.Four** across 9 files
9. **All DigitLevel.Sector → DigitLevel.One** across 2 files
10. **`CompositionTreeMap.tsx`**: Smart hierarchical filter (no double-counting), drill-down on click, enhanced tooltip (employees, share%, avg wage, total income), `aMean` in data
11. **`ClusterCompositionTreeMap.tsx`**: Enhanced tooltip (employees, share%, total income)
12. **`cityComposition/index.tsx`**: `onDrillDown` handler (isolate sector + increase digit level)
13. **`CitySearch.tsx`**: Region dropdown reordered — States before Metropolitan Areas
14. **`dataProvider/index.tsx`**: `fetchAndMerge()` for level keys, handles `4-metro` split
15. **`dataProvider/types.ts`**: Added `parentCode` to `BLSOccupation`
16. **`useGlobalIndustriesData.ts`**: Maps `parentCode` to `parentId` and `parentCode`

### Pipeline Output (4-Level)
- `bls-data.json` (meta catalog with "4-metro" in levelFiles)
- `bls-data-us-2024.json` — 1.8 MB (levels 1+2, 116 occupations)
- `bls-data-us-2024-3.json` — 719 KB (broad, 453 occupations)
- `bls-data-us-2024-4.json` — 6.0 MB (detailed, nat+state, 819 occupations)
- `bls-data-us-2024-4-metro.json` — 23 MB (detailed, metro only, 809 occupations)
- Old `bls-data-us-2024-5.json` deleted

### Validation Results
- 4 expected discrepancies (BLS data suppression): SOC 27-2000, 27-2010, 27-2030, 29-1210

## Pending
- Build frontend (`npm start`) and verify treemaps render correctly
- Footer still shows Harvard Growth Lab branding
- Some text still says "city" instead of "region"
- 23MB metro file may benefit from gzip in production
