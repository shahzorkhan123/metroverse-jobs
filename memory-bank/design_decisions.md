# Design Decisions

## 1. Keep adapter field names matching Metroverse
**Decision**: Use `naicsId`, `numEmploy`, `numCompany` in adapter output
**Rationale**: Minimizes changes to downstream components (CompositionTreeMap, charts, etc.)
**Trade-off**: Confusing naming (naicsId holds SOC code) but far fewer code changes

## 2. HashRouter instead of BrowserRouter
**Decision**: Use HashRouter for GitHub Pages
**Rationale**: GitHub Pages doesn't support SPA fallback routing. HashRouter uses URL fragments.
**Trade-off**: URLs look like `/#/region/state-california` instead of `/region/state-california`

## 3. Country-tagged split data files
**Decision**: Split JSON by country-year-level with meta catalog
**Rationale**: 182K BLS records produce ~60MB total. Split enables lazy loading of deeper levels.
**Trade-off**: More network requests, but levels 3+4 only loaded on demand

## 4. SOC 4-level hierarchy (not 5)
**Decision**: Map SOC codes to exactly 4 levels (major/minor/broad/detailed)
**Rationale**: BLS has 4 real levels. Our original level 3 (XX-XX00) was tiny — just SOC 2018 renumbered minor groups. Merging XX-XX00 into level 2 (minor) matches BLS reality.
**Trade-off**: XX-XX00 codes treated as level 2 even though they look different from XX-X000

## 5. Pipeline-level synthesis of missing SOC levels
**Decision**: Synthesize missing intermediate levels by aggregating children bottom-up
**Rationale**: BLS doesn't publish level 2 (minor group) for states/metros. Without synthesis, treemap shows nothing at level 2 for most regions.
**Trade-off**: Synthesized totals may not exactly match BLS suppressed data. But discrepancy is <0.3%.

## 6. Context-aware `_soc_parent()`
**Decision**: Accept `known_codes` set to resolve ambiguous level 3 parents
**Rationale**: Only 3 SOC codes use renumbered XX-XX00 pattern (15-1200, 31-1100, 51-5100). Without context, returning XX-XX00 for all level 3 codes creates phantom overlapping codes.
**Trade-off**: Requires passing code set through call chain. Safe default (XX-X000) when no context.

## 7. Level 3+4 split into nat+state vs metro files
**Decision**: Split levels 3 and 4 each into two files (nat+state and metro)
**Rationale**: Metro data is huge (17-23MB). State-level browsing shouldn't require loading metro data.
**Trade-off**: Frontend must fetch 2 files per level (handled automatically by loadLevel + fetchAndMerge)

## 8. Smart treemap filter with residual values
**Decision**: Show leaf nodes (finest available) per SOC branch. Parents with partial child coverage keep residual.
**Rationale**:
- Simple `level <= digitLevel` filter causes double-counting (parent + children both visible)
- Simply hiding parents loses uncovered employment from suppressed branches
- Residual = parent_total - children_sum preserves accuracy
**Trade-off**: More complex filter logic, but employment totals stay consistent across levels

## 9. Remove Mapbox map from landing page
**Decision**: Replace with hierarchical search dropdown
**Rationale**: Mapbox requires API key, adds complexity, and regions don't map well to city pins
**Trade-off**: Less visual landing page, but simpler and free

## 10. 22 SOC major group colors
**Decision**: Expand sectorColorMap from 9 to 22 entries
**Rationale**: BLS has 22 SOC major groups vs Metroverse's 9 NAICS sectors
**Trade-off**: More colors needed, some may be hard to distinguish

## 11. Complexity replaces Education
**Decision**: Map `yearsEducation` field to complexity score
**Rationale**: BLS2 uses complexity metric derived from O*NET, similar purpose to education years
**Trade-off**: Scales and meaning differ, but the UI pattern (gradient color) is identical

## 12. Dynamic maxDigitLevel from meta catalog
**Decision**: Compute max digit level from available level files rather than hardcoding
**Rationale**: Different datasets may have different depth (BLS=4, future NAICS=6)
**Trade-off**: Slight complexity in StaticDataProvider but more extensible
