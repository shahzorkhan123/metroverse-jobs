# Tasks TODO

## Sprint 1: Foundation
1. Remove deps: @apollo/client, graphql, mapbox-gl, react-mapbox-gl, react-city-space-mapbox, @sentry/react, @sentry/tracing, react-ga, react-ga4, @typeform/embed-react
2. Add LICENSE (CC BY-NC-SA 4.0 full text)
3. Add ATTRIBUTION.md
4. Update README.md
5. Create scripts/generate-static-data.py
6. Create src/dataProvider/types.ts
7. Create src/dataProvider/index.tsx
8. Update src/index.tsx (remove Apollo, add StaticDataProvider)
9. Update src/routing/routes.ts (city → region)

## Sprint 2: Core Viz
10. Rewrite src/hooks/useGlobalLocationData.ts
11. Rewrite src/hooks/useGlobalIndustriesData.ts
12. Rewrite src/hooks/useGlobalClusterData.ts
13. Rewrite src/hooks/useAggregateIndustriesData.ts
14. Stub src/hooks/useCurrentBenchmark.ts
15. Modify CompositionTreeMap.tsx (remove gql, use adapter)
16. Update sectorColorMap in styleUtils.ts (9 → 22 entries)

## Sprint 3: Pages
17. Rewrite landing page (region search dropdown)
18. Update profile page (3 tabs)
19. Create src/hooks/useVizOptions.ts
20. Update VIZ OPTIONS settings panel
21. Update Fluent strings (.ftl)
22. Disable/remove Phase 2 components

## Sprint 4: Deploy
23. Switch BrowserRouter → HashRouter
24. Add "homepage" to package.json
25. Create .github/workflows/deploy.yml
26. npm run build and test
27. Deploy to GitHub Pages
