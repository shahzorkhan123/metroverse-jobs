import { useStaticData } from '../dataProvider';
import {
  DigitLevel,
  ClusterLevel,
} from '../types/graphQL/graphQLTypes';
import { filterOutliers } from '../Utils';

/**
 * Adapter hook: replaces the aggregate industries GraphQL query.
 * Returns global min/max/median for wage (hourlyWage) and complexity (yearsEducation)
 * for color scaling in the treemap.
 *
 * Key mapping:
 *   yearsEducation -> complexity score
 *   hourlyWage -> annual mean wage (aMean)
 *   numEmploy -> totEmp
 *   numCompany -> gdp
 */

interface AggregateDatum {
  sumNumCompany: number;
  sumNumEmploy: number;
  avgNumCompany: number;
  avgNumEmploy: number;
}

interface IndustryDatum extends AggregateDatum {
  naicsId: number;
}

interface ClusterDatum extends AggregateDatum {
  clusterId: number;
}

export interface IndustryMap {
  globalMinMax: {
    minSumNumCompany: number;
    maxSumNumCompany: number;
    minSumNumEmploy: number;
    maxSumNumEmploy: number;
    minAvgNumCompany: number;
    maxAvgNumCompany: number;
    minAvgNumEmploy: number;
    maxAvgNumEmploy: number;
    minYearsEducation: number;
    medianYearsEducation: number;
    maxYearsEducation: number;
    minHourlyWage: number;
    medianHourlyWage: number;
    maxHourlyWage: number;
  };
  clusterMinMax: {
    minSumNumCompany: number;
    maxSumNumCompany: number;
    minSumNumEmploy: number;
    maxSumNumEmploy: number;
    minAvgNumCompany: number;
    maxAvgNumCompany: number;
    minAvgNumEmploy: number;
    maxAvgNumEmploy: number;
    minYearsEducation: number;
    maxYearsEducation: number;
    medianYearsEducation: number;
    minHourlyWage: number;
    medianHourlyWage: number;
    maxHourlyWage: number;
  };
  industries: {
    [id: string]: IndustryDatum & {
      yearsEducation: number;
      hourlyWage: number;
      yearsEducationRank: number;
      hourlyWageRank: number;
    };
  };
  clusters: {
    [id: string]: ClusterDatum & {
      yearsEducation: number;
      hourlyWage: number;
      yearsEducationRank: number;
      hourlyWageRank: number;
    };
  };
}

interface CoreVariables {
  level: DigitLevel;
  year: number;
  clusterLevel?: ClusterLevel;
}

const defaultMinMax = {
  minSumNumCompany: 0,
  maxSumNumCompany: 0,
  minSumNumEmploy: 0,
  maxSumNumEmploy: 0,
  minAvgNumCompany: 0,
  maxAvgNumCompany: 0,
  minAvgNumEmploy: 0,
  maxAvgNumEmploy: 0,
  minYearsEducation: 0,
  maxYearsEducation: 0,
  minHourlyWage: 0,
  maxHourlyWage: 0,
  medianHourlyWage: 0,
  medianYearsEducation: 0,
};

export const useAggregateIndustryMap = (variables: CoreVariables) => {
  const { data: blsData, loading, error } = useStaticData();

  const response: IndustryMap = {
    industries: {},
    clusters: {},
    globalMinMax: { ...defaultMinMax },
    clusterMinMax: { ...defaultMinMax },
  };

  if (!blsData) {
    return { loading, error, data: response };
  }

  const yearStr = variables.year.toString();
  const aggregates = blsData.aggregates[yearStr];

  if (!aggregates) {
    return { loading: false, error: undefined, data: response };
  }

  const { byOccupation } = aggregates;

  // Compute wage and complexity arrays for outlier filtering
  const wages = Object.values(byOccupation).map((o) => o.avgWage);
  const complexities = Object.values(byOccupation).map((o) => o.avgComplexity);

  const wagesFiltered = filterOutliers(wages);
  const complexitiesFiltered = filterOutliers(complexities);

  const sortedWages = [...wages].sort((a, b) => a - b);
  const sortedComplexities = [...complexities].sort((a, b) => a - b);
  const medianWage = sortedWages[Math.round(sortedWages.length / 2)] || 0;
  const medianComplexity = sortedComplexities[Math.round(sortedComplexities.length / 2)] || 0;

  const minWage = Math.min(...wagesFiltered);
  const maxWage = Math.max(...wagesFiltered);
  const minComplexity = Math.min(...complexitiesFiltered);
  const maxComplexity = Math.max(...complexitiesFiltered);

  response.globalMinMax = {
    ...response.globalMinMax,
    minYearsEducation: minComplexity,
    maxYearsEducation: maxComplexity,
    medianYearsEducation: medianComplexity,
    minHourlyWage: minWage,
    maxHourlyWage: maxWage,
    medianHourlyWage: medianWage,
  };
  // clusterMinMax mirrors globalMinMax for our flat structure
  response.clusterMinMax = { ...response.globalMinMax };

  // Build per-industry data
  for (const [socCode, occData] of Object.entries(byOccupation)) {
    const yearsEducation = occData.avgComplexity;
    const hourlyWage = occData.avgWage;

    let yearsEducationRank = yearsEducation < minComplexity ? minComplexity : yearsEducation;
    if (yearsEducationRank > maxComplexity) yearsEducationRank = maxComplexity;

    let hourlyWageRank = hourlyWage < minWage ? minWage : hourlyWage;
    if (hourlyWageRank > maxWage) hourlyWageRank = maxWage;

    response.industries[socCode] = {
      naicsId: parseInt(socCode, 10) || 0,
      sumNumCompany: 0,
      sumNumEmploy: occData.totalEmploy,
      avgNumCompany: 0,
      avgNumEmploy: 0,
      yearsEducation,
      hourlyWage,
      yearsEducationRank,
      hourlyWageRank,
    };
  }

  // Build per-cluster (major group) data - mirrors industries for our data
  for (const mg of blsData.majorGroups) {
    const matchingOccs = blsData.occupations
      .filter((o) => o.majorGroupId === mg.groupId)
      .map((o) => byOccupation[o.socCode])
      .filter(Boolean);

    const avgWage = matchingOccs.length > 0
      ? matchingOccs.reduce((s, o) => s + o.avgWage, 0) / matchingOccs.length
      : 0;
    const avgComplexity = matchingOccs.length > 0
      ? matchingOccs.reduce((s, o) => s + o.avgComplexity, 0) / matchingOccs.length
      : 0;

    let yearsEducationRank = avgComplexity < minComplexity ? minComplexity : avgComplexity;
    if (yearsEducationRank > maxComplexity) yearsEducationRank = maxComplexity;

    let hourlyWageRank = avgWage < minWage ? minWage : avgWage;
    if (hourlyWageRank > maxWage) hourlyWageRank = maxWage;

    response.clusters[mg.groupId] = {
      clusterId: parseInt(mg.groupId, 10),
      sumNumCompany: 0,
      sumNumEmploy: 0,
      avgNumCompany: 0,
      avgNumEmploy: 0,
      yearsEducation: avgComplexity,
      hourlyWage: avgWage,
      yearsEducationRank,
      hourlyWageRank,
    };
  }

  return { loading: false, error: undefined, data: response };
};

export default useAggregateIndustryMap;
