# Metroverse Jobs

A static visualization tool for US Bureau of Labor Statistics (BLS) occupation data, built on the [Metroverse](https://github.com/harvard-growth-lab/metroverse-front-end) frontend by Harvard Growth Lab.

## Features

- **Economic Composition Treemap**: Interactive canvas treemap showing occupation distribution by employment or GDP
- **Region Profiles**: View data for National, State, and Metropolitan regions
- **Multiple Color Modes**: Color by SOC Major Group, Annual Wage, or Complexity Score
- **Shareable URLs**: All filter settings encoded in URL query parameters
- **Static Deployment**: No backend required, works on GitHub Pages

## Data Sources

- [BLS Occupational Employment and Wage Statistics (OES)](https://www.bls.gov/oes/)
- [O*NET Online](https://www.onetonline.org/) (for complexity scores)

## Getting Started

```bash
npm install    # Install dependencies (Node 16 recommended)
npm start      # Dev server at localhost:3000
npm run build  # Production build
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
- **[react-panel-search](https://github.com/cid-harvard/react-panel-search)** - hierarchical search

## License

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) - Same as the original Metroverse.

## Attribution

Based on [Metroverse](https://metroverse.cid.harvard.edu/) by the Harvard Growth Lab, Center for International Development at Harvard University. See [ATTRIBUTION.md](ATTRIBUTION.md) for details.
