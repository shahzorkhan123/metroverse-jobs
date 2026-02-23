import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { BLSData, BLSMetaCatalog, CountryMetadata } from './types';

interface DataState {
  data: BLSData | null;
  loading: boolean;
  error: Error | null;
  /** Which levels have been loaded (e.g. [1, 2] initially, then [1,2,3] after loading level 3) */
  loadedLevels: number[];
  /** Trigger loading of a specific occupation level (3, 4, etc). No-op if already loaded. */
  loadLevel: (level: number) => void;
  /** True when a level extension file is currently being fetched */
  levelLoading: boolean;
  /** The meta catalog (available datasets, countries, years) */
  meta: BLSMetaCatalog | null;
  /** Highest digit level available in the data */
  maxDigitLevel: number;
  /** Currently selected country code (e.g. "us", "ind") */
  selectedCountry: string;
  /** Currently selected year */
  selectedYear: number;
  /** Metadata for the currently selected country */
  countryMetadata: CountryMetadata | null;
  /** Switch to a different country/year combination */
  switchCountryYear: (country: string, year: number) => void;
}

const BASE_URL = process.env.PUBLIC_URL + '/data';

const StaticDataContext = createContext<DataState>({
  data: null,
  loading: true,
  error: null,
  loadedLevels: [],
  loadLevel: () => {},
  levelLoading: false,
  meta: null,
  maxDigitLevel: 4,
  selectedCountry: 'us',
  selectedYear: 2024,
  countryMetadata: null,
  switchCountryYear: () => {},
});

export const useStaticData = () => useContext(StaticDataContext);

/**
 * Merge a level extension file into the existing BLSData.
 * Extension files contain only occupations at a single level,
 * so we add them additively to what's already loaded.
 */
function mergeExtension(base: BLSData, ext: BLSData): BLSData {
  // Merge occupations (add new ones)
  const existingCodes = new Set(base.occupations.map((o) => o.socCode));
  const newOccupations = ext.occupations.filter(
    (o) => !existingCodes.has(o.socCode),
  );

  // Merge majorGroups (add any new ones)
  const existingGroups = new Set(base.majorGroups.map((g) => g.groupId));
  const newGroups = ext.majorGroups.filter(
    (g) => !existingGroups.has(g.groupId),
  );

  // Merge regionData
  const mergedRegionData = { ...base.regionData };
  for (const [regionId, yearData] of Object.entries(ext.regionData)) {
    if (!mergedRegionData[regionId]) {
      mergedRegionData[regionId] = {};
    }
    for (const [year, records] of Object.entries(yearData)) {
      if (!mergedRegionData[regionId][year]) {
        mergedRegionData[regionId][year] = [];
      }
      // Append new occupation records (avoid duplicates by socCode)
      const existingSocs = new Set(
        mergedRegionData[regionId][year].map((r) => r.socCode),
      );
      const newRecords = records.filter((r) => !existingSocs.has(r.socCode));
      mergedRegionData[regionId][year] = [
        ...mergedRegionData[regionId][year],
        ...newRecords,
      ];
    }
  }

  // Merge aggregates
  const mergedAggregates = { ...base.aggregates };
  for (const [year, agg] of Object.entries(ext.aggregates)) {
    if (!mergedAggregates[year]) {
      mergedAggregates[year] = agg;
    } else {
      mergedAggregates[year] = {
        byOccupation: {
          ...mergedAggregates[year].byOccupation,
          ...agg.byOccupation,
        },
        minMaxStats: mergedAggregates[year].minMaxStats,
      };
    }
  }

  return {
    ...base,
    occupations: [...base.occupations, ...newOccupations],
    majorGroups: [...base.majorGroups, ...newGroups],
    regionData: mergedRegionData,
    aggregates: mergedAggregates,
  };
}

/** Find dataset entry for a given country+year */
function findDataset(meta: BLSMetaCatalog, country: string, year: number) {
  return meta.datasets.find(d => d.country === country && d.year === year);
}

/** Compute max digit level from meta catalog for a country+year */
function computeMaxDigitLevel(meta: BLSMetaCatalog, country: string, year: number): number {
  const dataset = findDataset(meta, country, year);
  if (!dataset) return 4;
  const key = `${country}-${year}`;
  const levelFiles = meta.levelFiles[key] || {};
  const allLevels = [
    ...dataset.levels,
    ...Object.keys(levelFiles).filter(k => /^\d+$/.test(k)).map(Number),
  ];
  return allLevels.length > 0 ? Math.max(...allLevels) : 4;
}

export const StaticDataProvider: React.FC = ({ children }) => {
  const [data, setData] = useState<BLSData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [loadedLevels, setLoadedLevels] = useState<number[]>([]);
  const [levelLoading, setLevelLoading] = useState(false);
  const [meta, setMeta] = useState<BLSMetaCatalog | null>(null);
  const [selectedCountry, setSelectedCountry] = useState('us');
  const [selectedYear, setSelectedYear] = useState(2024);

  // Track which levels are currently being fetched to avoid duplicate requests
  const levelFetchingRef = useRef<Set<number>>(new Set());

  // Track which level keys (e.g. "3", "4", "4-metro") have been loaded
  const loadedKeysRef = useRef<Set<string>>(new Set());

  // Initial load: fetch meta catalog, then fetch main data file
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        // Step 1: Fetch meta catalog
        const metaRes = await fetch(`${BASE_URL}/bls-data.json`);
        if (!metaRes.ok) throw new Error(`HTTP ${metaRes.status} fetching meta`);
        const metaData: BLSMetaCatalog = await metaRes.json();

        if (cancelled) return;
        setMeta(metaData);

        // Step 2: Determine initial country from URL or first dataset
        const urlParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
        const urlCountry = urlParams.get('country');
        const initialCountry = (urlCountry && metaData.countryMetadata[urlCountry])
          ? urlCountry
          : metaData.datasets[0]?.country || 'us';

        // Step 3: Pick the dataset for initial country
        const countryYears = metaData.yearsByCountry[initialCountry] || [];
        const initialYear = countryYears[countryYears.length - 1] || metaData.datasets[0]?.year || 2024;
        const dataset = findDataset(metaData, initialCountry, initialYear);

        if (!dataset) {
          throw new Error(`No dataset found for ${initialCountry}/${initialYear}`);
        }

        setSelectedCountry(initialCountry);
        setSelectedYear(initialYear);

        // Step 4: Fetch main data file
        const mainRes = await fetch(`${BASE_URL}/${dataset.file}`);
        if (!mainRes.ok) throw new Error(`HTTP ${mainRes.status} fetching ${dataset.file}`);
        const mainData: BLSData = await mainRes.json();

        if (cancelled) return;
        setData(mainData);
        setLoadedLevels(dataset.levels);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load BLS data:', err);
        setError(err instanceof Error ? err : new Error(String(err)));
        setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const fetchAndMerge = useCallback(
    (levelKey: string) => {
      if (
        loadedKeysRef.current.has(levelKey) ||
        levelFetchingRef.current.has(levelKey as any) ||
        !meta ||
        !data
      ) {
        return;
      }

      const key = `${selectedCountry}-${selectedYear}`;
      const levelFiles = meta.levelFiles[key];
      if (!levelFiles || !levelFiles[levelKey]) {
        return; // silently skip — not all splits exist
      }

      const filename = levelFiles[levelKey];
      levelFetchingRef.current.add(levelKey as any);
      setLevelLoading(true);

      fetch(`${BASE_URL}/${filename}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${filename}`);
          return res.json();
        })
        .then((extData: BLSData) => {
          setData((prev) => (prev ? mergeExtension(prev, extData) : prev));
          loadedKeysRef.current.add(levelKey);
          levelFetchingRef.current.delete(levelKey as any);
          setLevelLoading(levelFetchingRef.current.size > 0);
        })
        .catch((err) => {
          console.error(`Failed to load ${levelKey}:`, err);
          levelFetchingRef.current.delete(levelKey as any);
          setLevelLoading(levelFetchingRef.current.size > 0);
        });
    },
    [meta, data, selectedCountry, selectedYear],
  );

  const loadLevel = useCallback(
    (level: number) => {
      if (loadedLevels.includes(level)) return;

      // Load the main level file
      fetchAndMerge(String(level));

      // Also load the metro split if it exists (levels 3 and 4 are split)
      fetchAndMerge(`${level}-metro`);

      // Mark level as loaded (the actual merge happens async)
      setLoadedLevels((prev) => {
        if (prev.includes(level)) return prev;
        return [...prev, level].sort();
      });
    },
    [loadedLevels, fetchAndMerge],
  );

  const switchCountryYear = useCallback(
    (country: string, year: number) => {
      if (!meta) return;
      const dataset = findDataset(meta, country, year);
      if (!dataset) {
        console.warn(`No dataset for ${country}/${year}`);
        return;
      }

      setSelectedCountry(country);
      setSelectedYear(year);
      setLoading(true);
      setData(null);
      setLoadedLevels([]);
      loadedKeysRef.current = new Set();
      levelFetchingRef.current = new Set();

      fetch(`${BASE_URL}/${dataset.file}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${dataset.file}`);
          return res.json();
        })
        .then((mainData: BLSData) => {
          setData(mainData);
          setLoadedLevels(dataset.levels);
          setLoading(false);
        })
        .catch((err) => {
          console.error(`Failed to load dataset for ${country}/${year}:`, err);
          setError(err instanceof Error ? err : new Error(String(err)));
          setLoading(false);
        });
    },
    [meta],
  );

  // Compute highest available digit level from meta catalog for selected country
  const maxDigitLevel = meta
    ? computeMaxDigitLevel(meta, selectedCountry, selectedYear)
    : 4;

  // Get country metadata for the selected country
  const countryMetadata = meta?.countryMetadata?.[selectedCountry] || null;

  return (
    <StaticDataContext.Provider
      value={{
        data, loading, error, loadedLevels, loadLevel, levelLoading,
        meta, maxDigitLevel,
        selectedCountry, selectedYear, countryMetadata,
        switchCountryYear,
      }}
    >
      {children}
    </StaticDataContext.Provider>
  );
};
