# Metroverse Jobs

A static visualization tool for US Bureau of Labor Statistics (BLS) occupation data, built on the [Metroverse](https://github.com/harvard-growth-lab/metroverse-front-end) frontend by Harvard Growth Lab.

## Screenshots

### Landing Page
Region selector with National, Metropolitan, and State groupings.

![Landing Page](docs/screenshots/01-landing-page.png)

### Region Overview
3-dropdown navigation: Country, Year, and Region selector.

![Region Overview](docs/screenshots/02-overview-dropdowns.png)

### Economic Composition Treemap
Interactive treemap showing occupation distribution by employment share. US National data with 22 SOC major groups.

![Treemap - US National](docs/screenshots/03-treemap-composition.png)

### Viz Options Panel
Toggle between Employees/Income view, set digit level (1-6), color by sector/education/wage.

![Viz Options](docs/screenshots/04-viz-options.png)

### Tooltip with SOC Code
Hover any occupation to see SOC code, year, share, and employment count.

![Tooltip](docs/screenshots/05-treemap-tooltip.png)

### State-Level View (California)
Region switching updates treemap data. California shown with 58.1k workers across 22 occupation groups.

![California Treemap](docs/screenshots/06-california-treemap.png)

## Features

- **Economic Composition Treemap**: Interactive canvas treemap showing occupation distribution by employment or income
  - *Industry Groups*: 22 SOC major groups (US) / 9 NCO divisions (India), drillable to 4 levels
  - *Knowledge Clusters*: Same data grouped as "clusters" for Metroverse compatibility
  - *State Distribution* (national only): Each occupation group broken down across all states/UTs — ~1,100 cells
- **Time Series**: Stacked area chart of occupation employment over time (BLS OES 2003–2024, PLFS 2018–2024, ILOSTAT 1991–2025)
  - *State Breakdown mode*: Select any occupation to pivot layers from occupation groups → states
- **Region Profiles**: View data for National, State, and Metropolitan regions
- **Multi-Country**: United States (SOC/BLS) and India (NCO/PLFS) with country switcher
- **3-Dropdown Navigation**: Country, Year, and Region selectors
- **Multiple Color Modes**: Color by SOC Major Group, Annual Wage, or Complexity Score
- **Configurable Digit Levels**: View data at major group (1-digit) through detailed (4-digit) SOC/NCO levels
- **Shareable URLs**: All filter settings encoded in URL query parameters
- **Static Deployment**: No backend required, works on GitHub Pages

## Data Sources

### United States
- [BLS Occupational Employment and Wage Statistics (OES)](https://www.bls.gov/oes/)
- [O*NET Online](https://www.onetonline.org/) (for complexity scores)
- Coverage: National, 50 States, 400+ Metropolitan/Nonmetropolitan areas
- Occupation codes: SOC 2018 (4 levels: major group → detailed occupation)

### India
- [PLFS (Periodic Labour Force Survey)](https://www.mospi.gov.in/plfs) by MoSPI
- Coverage: National + 37 States/UTs (urban/rural, no metro-level)
- Occupation codes: NCO 2015 (4 levels: division → unit group)
- Structure: 1-digit NCO × State (employment + wages), 2-digit NCO × State (employment), 3-digit NCO × National
- Time series: 2018–2024 (employment), 2020–2024 (income)

## Getting Started

```bash
npm install    # Install dependencies (Node 16 recommended)
npm start      # Dev server at localhost:3000 (Windows: set NODE_OPTIONS=--openssl-legacy-provider first)
npm run build  # Production build
npx cross-env NODE_OPTIONS=--openssl-legacy-provider react-scripts build  # Windows-friendly build
```

### Running Tests
```bash
# Python pipeline tests (48 tests)
pytest tests/test_pipeline.py -v

# Playwright UI smoke tests (requires dev server on port 3000)
npm start &
npx playwright test tests/playwright/pre-checkin.spec.ts
```

No `.env` file is required - this project uses static data files instead of API calls.

## Generating Data

```bash
# Requires ../bls2/ project with pipeline data
python scripts/generate-static-data.py
```

## Primary Technologies

- **[TypeScript](https://www.typescriptlang.org/), v3.7** - core language
- **[React](https://reactjs.org/), v16.13** - core framework
- **[Styled Components](https://styled-components.com/), v5.1** - CSS-in-JS styling
- **[D3](https://d3js.org/), v5.16** - data processing and utilities
- **[Fluent](https://projectfluent.org/), v0.13** - internationalization
- **[react-canvas-treemap](https://github.com/cid-harvard/react-canvas-treemap)** - treemap visualization (MIT)

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) - Same as the original Metroverse.

## Attribution

Based on [Metroverse](https://metroverse.cid.harvard.edu/) by the Harvard Growth Lab, Center for International Development at Harvard University. See [ATTRIBUTION.md](ATTRIBUTION.md) for details.
