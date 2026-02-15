# Project Overview

## What
Fork of Harvard Growth Lab's Metroverse frontend, adapted to visualize US BLS occupation data as a static site.

## Why
Metroverse has beautiful treemaps, search, and comparison charts. Rather than building from scratch, we reuse the UI and replace the GraphQL data layer with static JSON.

## Tech Stack
- **Frontend**: React 16, TypeScript 3.7, react-scripts 3.4.3 (CRA)
- **Styling**: styled-components, polished
- **Viz**: react-canvas-treemap (MIT), react-fast-charts, react-comparison-bar-chart
- **Search**: react-panel-search (hierarchical dropdown)
- **i18n**: Fluent (fluent-react)
- **Routing**: react-router-dom 5 with HashRouter
- **Data**: Static JSON (bls-data.json), no backend

## Relationship to bls2
- bls2 (`D:\Projects\bls2`) is the data pipeline project
- metroverse-jobs reads bls2's output (job_data.js or bls.db) to generate bls-data.json
- Both projects are separate repos

## License
CC BY-NC-SA 4.0 (inherited from Metroverse)

## Deployment
GitHub Pages at https://shahzorkhan123.github.io/metroverse-jobs
