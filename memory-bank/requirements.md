# Requirements

## Phase 1 (Complete)
1. Landing page with region search (hierarchical dropdown, no map)
2. Region profile: Economic Composition treemap
3. Region profile: "Good At" comparison chart
4. Filter controls:
   - Top bar: Year, Region Type, Region dropdowns
   - VIZ OPTIONS panel: Size by (Employees/GDP), Color by (Sector/Wage/Complexity), Digit Level (1-4)
   - All filters encoded in URL query params (shareable links)
5. Color by: SOC Major Group / Wage / Complexity
6. Size by: Employment / GDP
7. All 3 region types: National, State, Metro
8. Static deployment (GitHub Pages, $0/month)
9. Attribution to Harvard Growth Lab

## Phase 2 (Complete)
1. Python pipeline fetching real BLS OES data (182K records)
2. SOC 4-level hierarchy (major/minor/broad/detailed)
3. Split data files by level with lazy loading
4. Smart treemap filter (no double-counting, leaf nodes only)
5. Treemap drill-down (click sector → isolate + zoom to next level)
6. Enhanced tooltips (employees, share%, avg wage, total income)
7. Pipeline synthesis of missing intermediate SOC levels
8. Region dropdown ordering: National → States → Metropolitan Areas
9. Data validation with `--validate` flag

## Phase 3 (Future)
- Multi-year support (2020-2024)
- RCA calculations for occupation specialization
- Industry/Occupation Space network graph
- Growth Opportunities (PSWOT chart)
- Similar Regions comparison
- Multi-country support

## Constraints
- No backend — pure static site
- CC BY-NC-SA 4.0 license
- Node 16 for build compatibility
- Must work on GitHub Pages (HashRouter)
- Large metro files (17-23MB) need gzip in production
