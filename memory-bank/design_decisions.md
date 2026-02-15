# Design Decisions

## 1. Keep adapter field names matching Metroverse
**Decision**: Use `naicsId`, `numEmploy`, `numCompany` in adapter output
**Rationale**: Minimizes changes to downstream components (CompositionTreeMap, charts, etc.)
**Trade-off**: Confusing naming (naicsId holds SOC code) but far fewer code changes

## 2. HashRouter instead of BrowserRouter
**Decision**: Use HashRouter for GitHub Pages
**Rationale**: GitHub Pages doesn't support SPA fallback routing. HashRouter uses URL fragments.
**Trade-off**: URLs look like `/#/region/state-california` instead of `/region/state-california`

## 3. Static JSON instead of per-region files
**Decision**: Single bls-data.json file with all data
**Rationale**: Simpler implementation, single fetch, small data size (~720 records for 2024)
**Trade-off**: Larger initial load, but data is small enough (<1MB)

## 4. Remove Mapbox map from landing page
**Decision**: Replace with hierarchical search dropdown
**Rationale**: Mapbox requires API key, adds complexity, and regions (National/State/Metro) don't map well to city pins
**Trade-off**: Less visual landing page, but simpler and free

## 5. 22 SOC major group colors
**Decision**: Expand sectorColorMap from 9 to 22 entries
**Rationale**: BLS has 22 SOC major groups vs Metroverse's 9 NAICS sectors
**Trade-off**: More colors needed, some may be hard to distinguish

## 6. Complexity replaces Education
**Decision**: Map `yearsEducation` field to complexity score
**Rationale**: BLS2 uses a complexity metric derived from O*NET, similar purpose to Metroverse's education years
**Trade-off**: Scales and meaning differ, but the UI pattern (gradient color) is identical
