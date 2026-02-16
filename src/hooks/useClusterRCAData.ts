import { useStaticData } from "../dataProvider";
import {
  ClusterLevel,
  CompositionType,
  defaultCompositionType,
} from "../types/graphQL/graphQLTypes";
import useCurrentCityId from "./useCurrentCityId";
import { defaultYear } from "../Utils";
import useQueryParams from "./useQueryParams";

export enum RegionGroup {
  World = "world",
  SimilarCities = "similarcities",
}

interface ClusterDensity {
  clusterId: string;
  densityCompany: number | null;
  densityEmploy: number | null;
}

interface ClusterRca {
  clusterId: string;
  rca: number | null;
  comparableIndustry: number | null;
}

interface ClusterData {
  clusterId: string;
  level: number | null;
  numCompany: number | null;
  numEmploy: number | null;
}

export interface SuccessResponse {
  clusterDensity: ClusterDensity[];
  clusterRca: ClusterRca[];
  clusterData: ClusterData[];
}

const useClusterRCAData = (_level: ClusterLevel) => {
  const cityId = useCurrentCityId();
  const { data: blsData, loading: blsLoading } = useStaticData();

  const { composition_type } = useQueryParams();

  const defaultCompositionVariable =
    defaultCompositionType === CompositionType.Companies ? "company" : "employ";
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  let _variable: "employ" | "company" = defaultCompositionVariable;
  if (composition_type === CompositionType.Companies) {
    _variable = "company";
  } else if (composition_type === CompositionType.Employees) {
    _variable = "employ";
  }

  if (cityId === null || blsLoading || !blsData) {
    return { loading: true, error: undefined, data: undefined };
  }

  const regionData = blsData.regionData[cityId];
  if (!regionData) {
    return { loading: false, error: undefined, data: undefined };
  }

  const yearData = regionData[defaultYear];
  if (!yearData) {
    return { loading: false, error: undefined, data: undefined };
  }

  // Build socCode → majorGroupId lookup
  const socToMajorGroup: Record<string, string> = {};
  blsData.occupations.forEach((o) => {
    socToMajorGroup[o.socCode] = o.majorGroupId;
  });

  // Build cluster data from occupations grouped by major group
  const clusterData: ClusterData[] = [];
  const clusterRca: ClusterRca[] = [];
  const clusterDensity: ClusterDensity[] = [];

  // Aggregate by major group
  const majorGroupAgg: Record<string, { employ: number; gdp: number }> = {};
  yearData.forEach((occ) => {
    const mgId = socToMajorGroup[occ.socCode] || "00";
    if (!majorGroupAgg[mgId]) {
      majorGroupAgg[mgId] = { employ: 0, gdp: 0 };
    }
    majorGroupAgg[mgId].employ += occ.totEmp;
    majorGroupAgg[mgId].gdp += occ.gdp;
  });

  Object.entries(majorGroupAgg).forEach(([mgId, agg]) => {
    clusterData.push({
      clusterId: mgId,
      level: 1,
      numCompany: agg.gdp,
      numEmploy: agg.employ,
    });
    // RCA placeholder: 1.0 for all (no cross-region comparison available)
    clusterRca.push({
      clusterId: mgId,
      rca: 1.0,
      comparableIndustry: null,
    });
    clusterDensity.push({
      clusterId: mgId,
      densityCompany: null,
      densityEmploy: null,
    });
  });

  const data: SuccessResponse = { clusterDensity, clusterRca, clusterData };
  return { loading: false, error: undefined, data };
};

export default useClusterRCAData;
