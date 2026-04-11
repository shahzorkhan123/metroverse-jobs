import { TimeSeriesFile, CountryMetadata } from '../dataProvider/types';
import { getStateAbbreviation } from './stateAbbreviations';

/**
 * Transforms time-series data to show state breakdown for a specific occupation.
 * Returns a virtual TimeSeriesFile where groups = states instead of occupations.
 *
 * @param data Original time-series data
 * @param nationalRegionId Region ID for national level (e.g., "national-us")
 * @param occupationGroupId The occupation group to break down by state (e.g., "29")
 * @param topN Number of top states to show individually, or 'all' to show all states
 * @param countryMetadata Country metadata for abbreviation lookup
 * @returns Virtual TimeSeriesFile with states as groups
 */
export function transformTimeSeriesByState(
  data: TimeSeriesFile,
  nationalRegionId: string,
  occupationGroupId: string,
  topN: number | 'all',
  countryMetadata: CountryMetadata | null,
): TimeSeriesFile {
  // Get state regions (exclude national)
  const stateRegions = data.regions.filter(
    r => r.regionType === 'State' && r.regionId !== nationalRegionId
  );

  if (stateRegions.length === 0) {
    // No state data, return empty structure
    return {
      ...data,
      groups: [],
      data: {},
    };
  }

  // Extract state employment for the selected occupation in the latest year
  const latestYear = data.metadata.years[data.metadata.years.length - 1];
  const stateEmployment: { regionId: string; name: string; emp: number }[] = [];

  stateRegions.forEach(region => {
    const regionData = data.data[region.regionId];
    if (!regionData || !regionData[occupationGroupId]) return;

    const occData = regionData[occupationGroupId];
    const latestIndex = data.metadata.years.indexOf(latestYear);
    const emp = occData.emp[latestIndex];

    if (emp !== null && emp !== undefined && emp > 0) {
      stateEmployment.push({
        regionId: region.regionId,
        name: region.name,
        emp,
      });
    }
  });

  // Sort by latest employment descending
  stateEmployment.sort((a, b) => b.emp - a.emp);

  // Determine which states to show individually
  let individualStates: typeof stateEmployment;
  let otherStates: typeof stateEmployment = [];

  if (topN === 'all') {
    individualStates = stateEmployment;
  } else {
    individualStates = stateEmployment.slice(0, topN);
    otherStates = stateEmployment.slice(topN);
  }

  // Build groups array (states as groups)
  const groups: { id: string; name: string; color?: string }[] = individualStates.map(s => ({
    id: s.regionId,
    name: getStateAbbreviation(s.name, countryMetadata),
    color: undefined, // Let StackedAreaChart assign colors
  }));

  // Add "Other" group if needed
  const hasOther = otherStates.length > 0;
  if (hasOther) {
    groups.push({
      id: '__other__',
      name: `Other (${otherStates.length} states)`,
      color: '#999999',
    });
  }

  // Build data object
  const transformedData: TimeSeriesFile['data'] = {
    [nationalRegionId]: {},
  };

  // Add individual states
  individualStates.forEach(state => {
    const regionData = data.data[state.regionId];
    if (!regionData || !regionData[occupationGroupId]) return;

    transformedData[nationalRegionId][state.regionId] = {
      emp: regionData[occupationGroupId].emp,
      gdp: regionData[occupationGroupId].gdp,
    };
  });

  // Aggregate "Other" states
  if (hasOther) {
    const empArrays: (number | null)[][] = [];
    const gdpArrays: (number | null)[][] = [];

    otherStates.forEach(state => {
      const regionData = data.data[state.regionId];
      if (!regionData || !regionData[occupationGroupId]) return;

      empArrays.push(regionData[occupationGroupId].emp);
      if (regionData[occupationGroupId].gdp) {
        gdpArrays.push(regionData[occupationGroupId].gdp || []);
      }
    });

    // Sum across states for each year
    const aggregatedEmp = data.metadata.years.map((_, yearIdx) => {
      let sum = 0;
      let hasValue = false;
      empArrays.forEach(arr => {
        const val = arr[yearIdx];
        if (val !== null && val !== undefined) {
          sum += val;
          hasValue = true;
        }
      });
      return hasValue ? sum : null;
    });

    const aggregatedGdp = data.metadata.hasGdp
      ? data.metadata.years.map((_, yearIdx) => {
          let sum = 0;
          let hasValue = false;
          gdpArrays.forEach(arr => {
            const val = arr[yearIdx];
            if (val !== null && val !== undefined) {
              sum += val;
              hasValue = true;
            }
          });
          return hasValue ? sum : null;
        })
      : undefined;

    transformedData[nationalRegionId]['__other__'] = {
      emp: aggregatedEmp,
      gdp: aggregatedGdp,
    };
  }

  return {
    metadata: data.metadata,
    groups,
    regions: [{ regionId: nationalRegionId, name: 'National', regionType: 'National' }],
    data: transformedData,
  };
}
