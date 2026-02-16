import { useStaticData } from "../../../../dataProvider";
import {
  DigitLevel,
  CompositionType,
  defaultCompositionType,
  isValidPeerGroup,
  PeerGroup,
} from "../../../../types/graphQL/graphQLTypes";
import useCurrentCityId from "../../../../hooks/useCurrentCityId";
import { defaultYear } from "../../../../Utils";
import useQueryParams from "../../../../hooks/useQueryParams";
import useCurrentBenchmark from "../../../../hooks/useCurrentBenchmark";

export enum RegionGroup {
  World = "world",
  SimilarCities = "similarcities",
}

interface ClusterData {
  clusterId: string;
  level: number | null;
  numEmploy: number | null;
}

interface NaicsData {
  naicsId: string;
  numCompany: number | null;
  numEmploy: number | null;
}

interface NaicsRca {
  naicsId: string;
  rca: number | null;
}

interface ClusterRca {
  clusterId: string;
  rca: number | null;
}

export interface SuccessResponse {
  clusterData: ClusterData[];
  naicsData: NaicsData[];
  naicsRca: NaicsRca[];
  c1Rca: ClusterRca[];
  c3Rca: ClusterRca[];
}

interface Variables {
  cityId: number | null;
  year: number;
  level: DigitLevel;
  peerGroup: PeerGroup | "";
  partnerCityIds: [number] | [];
  variable: "employ" | "company";
}

export const useClusterIntensityQuery = (variables: Variables) => {
  const { data: blsData, loading: blsLoading } = useStaticData();

  if (variables.cityId === null || blsLoading || !blsData) {
    return { loading: true, error: undefined, data: undefined };
  }

  const cityId = variables.cityId.toString();
  const regionData = blsData.regionData[cityId];
  if (!regionData) {
    return { loading: false, error: undefined, data: undefined };
  }

  const yearData = regionData[variables.year] || regionData[defaultYear];
  if (!yearData) {
    return { loading: false, error: undefined, data: undefined };
  }

  // Build socCode → majorGroupId lookup
  const socToMajorGroup: Record<string, string> = {};
  blsData.occupations.forEach((o) => {
    socToMajorGroup[o.socCode] = o.majorGroupId;
  });

  const naicsData: NaicsData[] = [];
  const naicsRca: NaicsRca[] = [];

  yearData.forEach((occ) => {
    naicsData.push({
      naicsId: occ.socCode,
      numCompany: occ.gdp,
      numEmploy: occ.totEmp,
    });
    naicsRca.push({
      naicsId: occ.socCode,
      rca: 1.0,
    });
  });

  // Aggregate by major group for cluster data
  const majorGroupAgg: Record<string, { employ: number }> = {};
  yearData.forEach((occ) => {
    const mgId = socToMajorGroup[occ.socCode] || "00";
    if (!majorGroupAgg[mgId]) {
      majorGroupAgg[mgId] = { employ: 0 };
    }
    majorGroupAgg[mgId].employ += occ.totEmp;
  });

  const clusterData: ClusterData[] = [];
  const c1Rca: ClusterRca[] = [];
  const c3Rca: ClusterRca[] = [];

  Object.entries(majorGroupAgg).forEach(([mgId, agg]) => {
    clusterData.push({
      clusterId: mgId,
      level: 1,
      numEmploy: agg.employ,
    });
    c1Rca.push({ clusterId: mgId, rca: 1.0 });
    c3Rca.push({ clusterId: mgId, rca: 1.0 });
  });

  const data: SuccessResponse = { clusterData, naicsData, naicsRca, c1Rca, c3Rca };
  return { loading: false, error: undefined, data };
};

const useRCAData = (level: DigitLevel) => {
  const cityId = useCurrentCityId();
  const { composition_type } = useQueryParams();
  const { benchmark } = useCurrentBenchmark();

  const defaultCompositionVariable =
    defaultCompositionType === CompositionType.Companies ? "company" : "employ";
  let variable: "employ" | "company" = defaultCompositionVariable;
  if (composition_type === CompositionType.Companies) {
    variable = "company";
  } else if (composition_type === CompositionType.Employees) {
    variable = "employ";
  }

  const peerGroup = isValidPeerGroup(benchmark) ? (benchmark as PeerGroup) : "";

  const partnerCityIds: [number] | [] =
    benchmark !== undefined && !isNaN(parseInt(benchmark, 10))
      ? [parseInt(benchmark, 10)]
      : [];

  const { loading, error, data } = useClusterIntensityQuery({
    cityId: cityId !== null ? parseInt(cityId, 10) : null,
    year: defaultYear,
    level,
    peerGroup,
    partnerCityIds,
    variable,
  });

  return cityId !== null
    ? { loading, error, data }
    : { loading: true, error: undefined, data: undefined };
};

export default useRCAData;
