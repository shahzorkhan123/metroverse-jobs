import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { BLSData, BLSMetaCatalog } from './types';

interface DataState {
  data: BLSData | null;
  loading: boolean;
  error: Error | null;
  /** Which levels have been loaded (e.g. [1, 2] initially, then [1,2,3] after loading level 3) */
  loadedLevels: number[];
  /** Trigger loading of a specific SOC level (3, 4, or 5). No-op if already loaded. */
  loadLevel: (level: number) => void;
  /** True when a level extension file is currently being fetched */
  levelLoading: boolean;
  /** The meta catalog (available datasets, countries, years) */
  meta: BLSMetaCatalog | null;
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

export const StaticDataProvider: React.FC = ({ children }) => {
  const [data, setData] = useState<BLSData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [loadedLevels, setLoadedLevels] = useState<number[]>([]);
  const [levelLoading, setLevelLoading] = useState(false);
  const [meta, setMeta] = useState<BLSMetaCatalog | null>(null);

  // Track which levels are currently being fetched to avoid duplicate requests
  const levelFetchingRef = useRef<Set<number>>(new Set());

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

        // Step 2: Pick the first dataset (default country/year)
        if (metaData.datasets.length === 0) {
          throw new Error('No datasets found in meta catalog');
        }
        const dataset = metaData.datasets[0];

        // Step 3: Fetch main data file (levels 1+2)
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

  const loadLevel = useCallback(
    (level: number) => {
      // Skip if already loaded or currently fetching
      if (
        loadedLevels.includes(level) ||
        levelFetchingRef.current.has(level) ||
        !meta ||
        !data
      ) {
        return;
      }

      // Find the level file in meta catalog
      // Try first dataset's country-year key
      const dataset = meta.datasets[0];
      if (!dataset) return;
      const key = `${dataset.country}-${dataset.year}`;
      const levelFiles = meta.levelFiles[key];
      if (!levelFiles || !levelFiles[String(level)]) {
        console.warn(`No level ${level} file found for ${key}`);
        return;
      }

      const filename = levelFiles[String(level)];
      levelFetchingRef.current.add(level);
      setLevelLoading(true);

      fetch(`${BASE_URL}/${filename}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${filename}`);
          return res.json();
        })
        .then((extData: BLSData) => {
          setData((prev) => (prev ? mergeExtension(prev, extData) : prev));
          setLoadedLevels((prev) => [...prev, level].sort());
          levelFetchingRef.current.delete(level);
          setLevelLoading(levelFetchingRef.current.size > 0);
        })
        .catch((err) => {
          console.error(`Failed to load level ${level}:`, err);
          levelFetchingRef.current.delete(level);
          setLevelLoading(levelFetchingRef.current.size > 0);
        });
    },
    [loadedLevels, meta, data],
  );

  return (
    <StaticDataContext.Provider
      value={{ data, loading, error, loadedLevels, loadLevel, levelLoading, meta }}
    >
      {children}
    </StaticDataContext.Provider>
  );
};
