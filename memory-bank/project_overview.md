# Project Overview

## What
Fork of Harvard Growth Lab's Metroverse frontend, adapted to visualize US BLS occupation data as a static site. Includes a Python pipeline that fetches real BLS OES data, processes it through SQLite, and exports split JSON files for lazy loading.

## Why
Metroverse has beautiful treemaps, search, and comparison charts. Rather than building from scratch, we reuse the UI and replace the GraphQL data layer with static JSON.

## Tech Stack
- **Frontend**: React 16, TypeScript 3.7, react-scripts 3.4.3 (CRA)
- **Styling**: styled-components, polished
- **Viz**: react-canvas-treemap (MIT), react-fast-charts, react-comparison-bar-chart
- **Search**: react-panel-search (hierarchical dropdown)
- **i18n**: Fluent (fluent-react)
- **Routing**: react-router-dom 5 with HashRouter
- **Data**: Static JSON files (lazy-loaded by level), no backend
- **Pipeline**: Python 3, requests, openpyxl, SQLite
- **Tests**: pytest (48 tests for pipeline)

## Data Source
- BLS Occupational Employment and Wage Statistics (OES) — bls.gov
- 182,187 records: national + 51 states + 380 metropolitan areas
- SOC 4-level hierarchy: major (22) → minor → broad → detailed (~820 occupations)

## Relationship to bls2
- bls2 (`D:\Projects\bls2`) is the original static visualization project (Plotly treemaps)
- metroverse-jobs (`D:\Projects\metroverse-jobs`) is the React fork with superior UI
- Pipeline lives in metroverse-jobs (`scripts/pipeline/`)
- Both projects are separate repos

## License
CC BY-NC-SA 4.0 (inherited from Metroverse)

## Deployment
GitHub Pages at https://shahzorkhan123.github.io/metroverse-jobs
Local dev: `npm start` → localhost:3000
Local serve: `npx serve -s build -l 8080` or `python -m http.server 8080`
