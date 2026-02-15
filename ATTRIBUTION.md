# Attribution

This project is a fork of **Metroverse** by the **Harvard Growth Lab**.

## Original Project

- **Name**: Metroverse
- **Authors**: Harvard Growth Lab, Center for International Development at Harvard University
- **Repository**: https://github.com/harvard-growth-lab/metroverse-front-end
- **Website**: https://metroverse.cid.harvard.edu/
- **License**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)

## Modifications

This fork (metroverse-jobs) replaces the original Metroverse data layer (GraphQL API backed by PostgreSQL with international city/industry data) with static JSON files containing US Bureau of Labor Statistics (BLS) occupation data. Key changes include:

- Replaced Apollo/GraphQL data fetching with a static JSON data provider
- Replaced NAICS industry classification with SOC (Standard Occupational Classification) occupation data
- Replaced international city data with US National, State, and Metropolitan region data
- Removed Mapbox map from landing page (replaced with search interface)
- Removed Sentry error tracking, Google Analytics, and Typeform survey
- Added BLS-specific filter controls (Year, Region Type, Region)
- Adapted color schemes for 22 SOC major groups (vs. 9 NAICS sectors)

## Data Sources

- **BLS Occupational Employment and Wage Statistics (OES)**: https://www.bls.gov/oes/
- **O*NET Online**: https://www.onetonline.org/

## License

This work is licensed under the same terms as the original: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
