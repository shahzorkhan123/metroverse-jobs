import { useEffect } from 'react';
import { useStaticData } from '../dataProvider';
import useQueryParams from './useQueryParams';
import { DigitLevel } from '../types/graphQL/graphQLTypes';

const defaultDigitLevel = DigitLevel.Two;

/**
 * Hook that watches the digit_level query param and triggers
 * lazy-loading of level extension data when the user selects
 * level 3, 4, or 5 in the Settings panel.
 *
 * Import and call this hook in any page that uses digit_level filtering.
 * It's a no-op if the level data is already loaded.
 */
export const useLevelLoader = () => {
  const { digit_level } = useQueryParams();
  const { loadLevel, loadedLevels, levelLoading } = useStaticData();

  const digitLevel = digit_level
    ? parseInt(digit_level, 10)
    : defaultDigitLevel;

  useEffect(() => {
    // Load all levels up to the selected digit level
    for (let lvl = 3; lvl <= digitLevel; lvl++) {
      if (!loadedLevels.includes(lvl)) {
        loadLevel(lvl);
      }
    }
  }, [digitLevel, loadLevel, loadedLevels]);

  return { levelLoading, loadedLevels, digitLevel };
};
