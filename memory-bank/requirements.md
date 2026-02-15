# Requirements

## Phase 1 (Current)
1. Landing page with region search (hierarchical dropdown, no map)
2. Region profile: Economic Composition treemap
3. Region profile: "Good At" comparison chart
4. Filter controls:
   - Top bar: Year, Region Type, Region dropdowns
   - VIZ OPTIONS panel: Size by (Employees/GDP), Color by (Sector/Wage/Complexity), Aggregation, Occupation Limit
   - All filters encoded in URL query params (shareable links)
5. Color by: SOC Major Group / Wage / Complexity
6. Size by: Employment / GDP
7. All 3 region types: National, State, Metro
8. Static deployment (GitHub Pages, $0/month)
9. Attribution to Harvard Growth Lab

## Phase 2 (Future)
- 5-digit detailed SOC occupations
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
