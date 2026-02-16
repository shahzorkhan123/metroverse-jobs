# Active Context

## Current Focus
REBRANDING COMPLETE & VERIFIED. All pages updated to "Metroverse-Jobs" branding with proper attribution.

## Completed So Far
- **Task #1**: Fork & clone → shahzorkhan123/metroverse-jobs
- **Task #2**: Cleaned package.json, added ATTRIBUTION.md, LICENSE, README.md
- **Task #3**: `scripts/generate-static-data.py` → `public/data/bls-data.json` (141KB)
- **Task #4**: StaticDataProvider + 5 adapter hooks rewritten
- **Task #8**: CLAUDE.md + memory-bank
- **Task #6**: All component modifications complete — build compiles with zero errors
- **Task #7**: Runtime verified — treemap renders with real BLS data

## Recent Changes (Rebranding for GitHub Pages)
- **Logo**: `src/assets/icons/cities-logo.svg` → text-based "METROVERSE-JOBS" (Segoe UI/Arial)
- **Favicon**: `public/favicon.svg` → "MVJ" with dark/light mode support
- **Page title**: `public/index.html` → "Metroverse-Jobs | BLS Occupation Data"
- **Manifest**: `public/manifest.json` → short_name "MVJ", name "Metroverse-Jobs"
- **GlobalStyles**: "Help us improve Metroverse-Jobs"
- **Default digit level**: Changed to Level 2 (2-digit SOC groups)
- **CompositionType**: "Establishments" → "Income"
- **Tooltip**: "Number of Establishments" → "Income"
- **Node sizing labels**: "Global income" / "Income in Region"
- **messages.ftl massive rewrite**:
  - Meta/app titles → "Metroverse-Jobs"
  - Landing: "Pick a region", "Type a region name", "use the search"
  - Landing modal: About BLS regions (National, State, Metro)
  - About: 5 sections (What is MVJ, Attribution & Credits, Data Sources, Methodology, Original Metroverse)
  - FAQ: 10 Q&As rewritten for this fork
  - Contact: GitHub Issues link + attribution disclaimer
- **README**: Updated with 6 screenshots and feature descriptions
- **Screenshots**: All 6 updated in `docs/screenshots/` with new branding

## Build Info
- Build command: `pushd "D:/Projects/metroverse-jobs" && NODE_OPTIONS="--openssl-legacy-provider --max-old-space-size=4096" npx react-scripts build`
- Serve: copy build/ → build-serve/metroverse-jobs/ → `npx serve build-serve -l PORT`
- Currently serving on port 3092

## Pending Tasks
- **Task #5**: Filter controls & useVizOptions hook (Future enhancement)
- **Task #9**: Split data files by SOC digit level (bls-data-us-2024-2.json etc.)
- Footer still shows Harvard Growth Lab branding (separate component, not in current scope)
- "Similar Cities Beta" header link still present
- Some text still says "city" instead of "region"
