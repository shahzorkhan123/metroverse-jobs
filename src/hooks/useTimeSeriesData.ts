import { useState, useEffect, useCallback, useMemo } from 'react';
import { useStaticData } from '../dataProvider';
import { TimeSeriesFile } from '../dataProvider/types';

const BASE_URL = process.env.PUBLIC_URL + '/data';

/** Describes a time-series data source available for the current country */
export interface TimeSeriesSource {
  id: string;          // e.g. "oes", "ilostat"
  label: string;       // e.g. "BLS OES (2003-2024, 22 groups)"
  hasMetro: boolean;
}

interface UseTimeSeriesResult {
  /** Available data sources for the current country */
  sources: TimeSeriesSource[];
  /** Currently selected source ID */
  selectedSourceId: string | null;
  /** Set the selected source */
  setSelectedSourceId: (id: string) => void;
  /** Loaded time-series data for the selected source */
  selectedData: TimeSeriesFile | null;
  /** Whether data is currently loading */
  loading: boolean;
  /** Error if any */
  error: string | null;
}

// Module-level cache to avoid re-fetching
const fileCache: { [url: string]: TimeSeriesFile } = {};

/** Source labels by ID */
const SOURCE_LABELS: { [id: string]: string } = {
  oes: 'BLS OES',
  ilostat: 'ILOSTAT Modelled Estimates',
  plfs: 'PLFS Annual Reports',
  combined: 'Combined EUS+PLFS',
};

function buildLabel(id: string, data: TimeSeriesFile | null): string {
  const base = SOURCE_LABELS[id] || id;
  if (data) {
    const years = data.metadata.years;
    const range = years.length > 0
      ? `${years[0]}-${years[years.length - 1]}`
      : '';
    return `${base} (${range}, ${data.groups.length} groups)`;
  }
  return base;
}

export default function useTimeSeriesData(regionId: string | null): UseTimeSeriesResult {
  const { meta, selectedCountry } = useStaticData();
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [loadedFiles, setLoadedFiles] = useState<{ [key: string]: TimeSeriesFile }>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Discover available sources for the current country
  const sourceEntries = useMemo(() => {
    if (!meta || !meta.timeseriesFiles) return [];
    const countryFiles = meta.timeseriesFiles[selectedCountry];
    if (!countryFiles) return [];
    return Object.keys(countryFiles).map(sourceId => ({
      sourceId,
      config: countryFiles[sourceId],
    }));
  }, [meta, selectedCountry]);

  // Auto-select first source when country changes
  useEffect(() => {
    if (sourceEntries.length > 0) {
      setSelectedSourceId(prev => {
        // Keep current selection if still valid
        if (prev && sourceEntries.some(s => s.sourceId === prev)) {
          return prev;
        }
        return sourceEntries[0].sourceId;
      });
    } else {
      setSelectedSourceId(null);
    }
  }, [sourceEntries]);

  // Determine whether the region needs metro data
  const needsMetro = useMemo(() => {
    if (!regionId) return false;
    return regionId.startsWith('metro-');
  }, [regionId]);

  // Fetch the selected source's data files
  const fetchSource = useCallback((sourceId: string) => {
    if (!meta || !meta.timeseriesFiles) return;
    const countryFiles = meta.timeseriesFiles[selectedCountry];
    if (!countryFiles || !countryFiles[sourceId]) return;

    const sourceConfig = countryFiles[sourceId];
    const baseUrl = `${BASE_URL}/${sourceConfig.base}`;
    const cacheKey = `${selectedCountry}-${sourceId}`;

    // Already cached?
    if (fileCache[baseUrl]) {
      setLoadedFiles(prev => ({ ...prev, [cacheKey]: fileCache[baseUrl] }));

      // Also fetch metro if needed
      if (needsMetro && sourceConfig.metro) {
        const metroUrl = `${BASE_URL}/${sourceConfig.metro}`;
        if (fileCache[metroUrl]) {
          // Merge metro into base
          const merged = mergeTimeSeriesFiles(fileCache[baseUrl], fileCache[metroUrl]);
          setLoadedFiles(prev => ({ ...prev, [cacheKey]: merged }));
        } else {
          setLoading(true);
          fetch(metroUrl)
            .then(res => {
              if (!res.ok) throw new Error(`HTTP ${res.status}`);
              return res.json();
            })
            .then((metroData: TimeSeriesFile) => {
              fileCache[metroUrl] = metroData;
              const merged = mergeTimeSeriesFiles(fileCache[baseUrl], metroData);
              setLoadedFiles(prev => ({ ...prev, [cacheKey]: merged }));
              setLoading(false);
            })
            .catch(err => {
              console.error(`Failed to load metro timeseries:`, err);
              setLoading(false);
            });
        }
      }
      return;
    }

    setLoading(true);
    setError(null);

    fetch(baseUrl)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: TimeSeriesFile) => {
        fileCache[baseUrl] = data;
        setLoadedFiles(prev => ({ ...prev, [cacheKey]: data }));

        // Also fetch metro if needed
        if (needsMetro && sourceConfig.metro) {
          const metroUrl = `${BASE_URL}/${sourceConfig.metro}`;
          return fetch(metroUrl)
            .then(res => {
              if (!res.ok) throw new Error(`HTTP ${res.status}`);
              return res.json();
            })
            .then((metroData: TimeSeriesFile) => {
              fileCache[metroUrl] = metroData;
              const merged = mergeTimeSeriesFiles(data, metroData);
              setLoadedFiles(prev => ({ ...prev, [cacheKey]: merged }));
            });
        }
        return undefined;
      })
      .then(() => setLoading(false))
      .catch(err => {
        console.error(`Failed to load timeseries ${sourceId}:`, err);
        setError(`Failed to load data: ${err.message}`);
        setLoading(false);
      });
  }, [meta, selectedCountry, needsMetro]);

  // Fetch when source changes
  useEffect(() => {
    if (selectedSourceId) {
      const cacheKey = `${selectedCountry}-${selectedSourceId}`;
      if (!loadedFiles[cacheKey]) {
        fetchSource(selectedSourceId);
      }
    }
  }, [selectedSourceId, selectedCountry, fetchSource, loadedFiles]);

  // Build sources list
  const sources: TimeSeriesSource[] = useMemo(() => {
    return sourceEntries.map(({ sourceId, config: cfg }) => {
      const cacheKey = `${selectedCountry}-${sourceId}`;
      const data = loadedFiles[cacheKey] || null;
      return {
        id: sourceId,
        label: buildLabel(sourceId, data),
        hasMetro: !!cfg.metro,
      };
    });
  }, [sourceEntries, selectedCountry, loadedFiles]);

  // Get the current data
  const selectedData = useMemo(() => {
    if (!selectedSourceId) return null;
    const cacheKey = `${selectedCountry}-${selectedSourceId}`;
    return loadedFiles[cacheKey] || null;
  }, [selectedSourceId, selectedCountry, loadedFiles]);

  return {
    sources,
    selectedSourceId,
    setSelectedSourceId,
    selectedData,
    loading,
    error,
  };
}

/** Merge a metro extension file into the base time-series file */
function mergeTimeSeriesFiles(base: TimeSeriesFile, metro: TimeSeriesFile): TimeSeriesFile {
  const mergedRegions = [...base.regions];
  const mergedData = { ...base.data };

  metro.regions.forEach(r => {
    if (!mergedRegions.some(br => br.regionId === r.regionId)) {
      mergedRegions.push(r);
    }
  });

  Object.keys(metro.data).forEach(regionId => {
    if (!mergedData[regionId]) {
      mergedData[regionId] = metro.data[regionId];
    }
  });

  return {
    ...base,
    regions: mergedRegions,
    data: mergedData,
  };
}
