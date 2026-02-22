# Active Context

## Current Focus
India PLFS data exploration complete. MoSPI MCP server configured. Data structure validated for multi-country support.

## What Was Done (2026-02-22, Session 4)

### India PLFS Data Research
1. **MoSPI MCP Server Integration**:
   - Configured official MoSPI Statistics MCP server (https://mcp.mospi.gov.in)
   - Tested PLFS API: 8 indicators available (LFPR, WPR, UR, wages, worker distribution)
   - API provides 1-digit NCO only, no occupation×wage cross-tabulations
   - Conclusion: MCP server insufficient for detailed occupation data

2. **PLFS Data Structure Analysis**:
   - **NCO 2015 Hierarchy**: 10 divisions (1-digit), ~30 sub-divisions (2-digit), ~116 groups (3-digit), ~436 unit groups (4-digit)
   - **Published tables**: Table 50 has 1-digit NCO × State wages (validated by MOSPI)
   - **Sample size**: ~100K households, ~418K persons, ~4,000 workers per state average
   - **Survey weights**: `mult` field (10-digit) required for population estimation

3. **Data Availability Assessment**:
   - State level: 1-digit NCO reliable (400 workers/occupation/state), 2-digit feasible (133 workers/occupation/state)
   - National level: 1-digit, 2-digit, 3-digit all reliable
   - 3-digit × State: Too sparse (~35 workers/occupation/state), requires suppression
   - NSS EUS (discontinued 2011), ASI (industry not occupation), DGET (too narrow) - all rejected

4. **Proposed India Structure**:
   ```
   State level:    1-digit NCO (10 divisions) × 37 States/UTs = 370 cells [default]
                   2-digit NCO (~30 sub-divisions) × 37 States/UTs = ~1,110 cells [with suppression]
   National level: 1-digit (10) + 2-digit (~30) + 3-digit (~116) NCO = 156 occupation categories
   ```
   Mirrors BLS OEWS structure (major groups at state, detailed at national)

5. **MCP Servers Configured** (6 total):
   - GitHub (global)
   - MoSPI Statistics (https://mcp.mospi.gov.in)
   - Fetch (web scraping)
   - Sequential Thinking (planning)
   - Memory (persistent context)

6. **Other Datasets Evaluated**:
   - ILOSTAT: 1-digit ISCO-08 only, no wages for India
   - ASI: NIC (industry) not NCO (occupation) - rejected
   - DGET: Vocational training sector only - rejected

## What Was Done (2026-02-22, Session 3)

### Pipeline: Synthesis of Missing SOC Levels
1. **`export_json.py`**: Added `_synthesize_missing_levels()` — bottom-up aggregation
   - BLS doesn't publish level 2 (minor group) for states/metros
   - Synthesis: level 3 from level 4 children, then level 2 from level 3
   - Uses `all_codes` (from all records including national) for parent resolution
   - Called inside `_build_static_data()` before level filtering

2. **Context-aware `_soc_parent()`** (Python + TypeScript):
   - Only 3 SOC codes use renumbered XX-XX00 pattern: `15-1200`, `31-1100`, `51-5100`
   - For level 3 (XX-XXX0): tries XX-XX00 first, falls back to XX-X000
   - Accepts `known_codes` set parameter; without context, defaults to XX-X000 (safe)
   - Fixed critical double-counting bug: aggressive fix created 15 phantom codes, adding 19.35M employees

3. **Level 3 file split** (matching level 4 pattern):
   - `bls-data-us-2024-3.json` — nat+state (3.7MB)
   - `bls-data-us-2024-3-metro.json` — metro only (17MB)
   - Frontend `loadLevel()` generalized to fetch `{level}-metro` for any level

### Frontend: Smart Treemap with Residuals
4. **Residual value computation** in `CompositionTreeMap.tsx`:
   - When parent has children that don't fully cover its employment, parent stays visible with residual = parent_total - children_sum
   - `adjustedValueMap` for consistent tooltip display
   - Uses `.forEach()` on Maps (not `for...of`) to avoid TS downlevelIteration issue

### Verification Results (US National)
- Level 1: 154,187,380 employees
- Level 2: 154,186,320 (diff: -1,060, ~0%)
- Level 3: 154,545,940 (+0.23%)
- Level 4: 147,659,390 (95.8% coverage — BLS suppression)
- Zero overlapping codes between levels
- 48 tests pass

### Pipeline Output (Final)
- `bls-data.json` — meta catalog (lists 3-metro and 4-metro)
- `bls-data-us-2024.json` — 8.0 MB (levels 1+2 with synthesis, 116 occ)
- `bls-data-us-2024-3.json` — 3.7 MB (broad, nat+state)
- `bls-data-us-2024-3-metro.json` — 17 MB (broad, metro)
- `bls-data-us-2024-4.json` — 6.0 MB (detailed, nat+state, 819 occ)
- `bls-data-us-2024-4-metro.json` — 23 MB (detailed, metro, 809 occ)

## What Was Done (2026-02-16, Session 2)
- SOC 4-level remap (was 5 levels)
- Smart treemap filter (no double-counting, hierarchical leaf selection)
- Treemap drill-down (click sector → isolate + increase digit level)
- Enhanced tooltips (employees, share%, avg wage, total income)
- DigitLevel enum 4 values, settings panel, region dropdown reorder
- Level 4 split (nat+state vs metro)
- Data validation (parentCode, completeness check)
- 48 tests passing

## Pending
- Footer still shows Harvard Growth Lab branding
- Some text still says "city" instead of "region"
- Large file sizes (8MB main, 17+23MB metro) — gzip recommended in production
- GDP/income validation (values shift across levels due to aMean rounding in synthesis)
- GitHub Actions CI/CD and GitHub Pages deployment
