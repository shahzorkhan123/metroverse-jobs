import React, { createContext, useContext, useEffect, useState } from 'react';
import { BLSData } from './types';

interface DataState {
  data: BLSData | null;
  loading: boolean;
  error: Error | null;
}

const StaticDataContext = createContext<DataState>({
  data: null,
  loading: true,
  error: null,
});

export const useStaticData = () => useContext(StaticDataContext);

export const StaticDataProvider: React.FC = ({ children }) => {
  const [state, setState] = useState<DataState>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    fetch(process.env.PUBLIC_URL + '/data/bls-data.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: BLSData) => {
        setState({ data, loading: false, error: null });
      })
      .catch((error) => {
        console.error('Failed to load BLS data:', error);
        setState({ data: null, loading: false, error });
      });
  }, []);

  return (
    <StaticDataContext.Provider value={state}>
      {children}
    </StaticDataContext.Provider>
  );
};
