import { useEffect, useState } from 'react';
import { useStaticData } from '../dataProvider';
import { SpaceFile, ComplexityFile } from '../dataProvider/types';
import useQueryParams from './useQueryParams';
import { SpaceType, defaultSpaceType } from '../routing/routes';

const BASE_URL = process.env.PUBLIC_URL + '/data';

// Module-level cache shared by every component that shows a space
const fileCache: { [url: string]: SpaceFile | ComplexityFile } = {};
const pending: { [url: string]: Promise<any> } = {};

const fetchCached = <T>(url: string): Promise<T> => {
  if (fileCache[url]) {
    return Promise.resolve(fileCache[url] as unknown as T);
  }
  if (!pending[url]) {
    pending[url] = fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        fileCache[url] = json;
        delete pending[url];
        return json;
      })
      .catch((err) => {
        delete pending[url];
        throw err;
      });
  }
  return pending[url];
};

interface Output<T> {
  loading: boolean;
  error: string | undefined;
  data: T | undefined;
}

/** File names for the current country/year, or undefined if none exist. */
export const useSpaceFiles = () => {
  const { meta, selectedCountry, selectedYear } = useStaticData();
  if (!meta || !meta.spaceFiles || !meta.spaceFiles[selectedCountry]) {
    return undefined;
  }
  const byYear = meta.spaceFiles[selectedCountry];
  return byYear[selectedYear.toString()] || byYear[Object.keys(byYear).sort().pop() as string];
};

/** The space shown on the Occupation Space tab (?space=occupation|job). */
export const useCurrentSpaceType = (): SpaceType => {
  const { space } = useQueryParams();
  return space === SpaceType.job ? SpaceType.job : defaultSpaceType;
};

const useJsonFile = <T>(file: string | undefined): Output<T> => {
  const url = file ? `${BASE_URL}/${file}` : undefined;
  const [output, setOutput] = useState<Output<T>>(() =>
    url && fileCache[url]
      ? { loading: false, error: undefined, data: fileCache[url] as unknown as T }
      : { loading: !!url, error: undefined, data: undefined },
  );

  useEffect(() => {
    let cancelled = false;
    if (!url) {
      setOutput({ loading: false, error: undefined, data: undefined });
      return;
    }
    if (fileCache[url]) {
      setOutput({ loading: false, error: undefined, data: fileCache[url] as unknown as T });
      return;
    }
    setOutput({ loading: true, error: undefined, data: undefined });
    fetchCached<T>(url)
      .then((data) => {
        if (!cancelled) setOutput({ loading: false, error: undefined, data });
      })
      .catch((err) => {
        console.error(`Failed to load ${url}:`, err);
        if (!cancelled) setOutput({ loading: false, error: err.message, data: undefined });
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  return output;
};

/** Layout (nodes, links, clusters) for the requested space. */
export const useSpaceLayout = (kind?: SpaceType): Output<SpaceFile> => {
  const files = useSpaceFiles();
  const current = useCurrentSpaceType();
  const spaceType = kind ? kind : current;
  return useJsonFile<SpaceFile>(files ? files[spaceType] : undefined);
};

/** PCI / JCI / ECI for the current country. */
export const useComplexityData = (): Output<ComplexityFile> => {
  const files = useSpaceFiles();
  return useJsonFile<ComplexityFile>(files ? files.complexity : undefined);
};
