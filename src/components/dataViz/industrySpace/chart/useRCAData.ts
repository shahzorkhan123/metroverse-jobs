import { useMemo } from "react";
import { useStaticData } from "../../../../dataProvider";
import { BLSData } from "../../../../dataProvider/types";
import { DigitLevel } from "../../../../types/graphQL/graphQLTypes";
import useCurrentCityId from "../../../../hooks/useCurrentCityId";
import { defaultYear } from "../../../../Utils";

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

/** Space clusters membership, when RCA is wanted for space knowledge clusters */
export interface ClusterMembership {
  nodes: { id: string; continent: string; country: string }[];
}

interface Variables {
  cityId: string | null;
  year: number;
  clusters?: ClusterMembership;
}

/**
 * Relative presence (Balassa RCA) of each occupation in a region, against
 * the national economy:
 *
 *   RCA(r, o) = (emp(r, o) / emp(r)) / (emp(nat, o) / emp(nat))
 *
 * Totals use the region's major-group (level 1) records so shares are
 * comparable across SOC levels.  Cluster RCA uses SOC major groups, or the
 * Occupation/Job Space knowledge clusters when `clusters` is given.
 */
export const useClusterIntensityQuery = (variables: Variables) => {
  const { data: blsData, loading: blsLoading } = useStaticData();
  const { cityId, year, clusters } = variables;
  const clusterNodes = clusters ? clusters.nodes : undefined;
  // Memoised so chart effects keyed on `data` only re-run when inputs change
  return useMemo(
    () =>
      computeIntensity(blsData, blsLoading, {
        cityId,
        year,
        clusters: clusterNodes ? { nodes: clusterNodes } : undefined,
      }),
    [blsData, blsLoading, cityId, year, clusterNodes],
  );
};

const computeIntensity = (
  blsData: BLSData | null,
  blsLoading: boolean,
  variables: Variables,
) => {
  if (variables.cityId === null || blsLoading || !blsData) {
    return { loading: true, error: undefined, data: undefined };
  }

  const cityId = variables.cityId;
  const regionData = blsData.regionData[cityId];
  const national = blsData.regions.find((r) => r.regionType === "National");
  if (!regionData || !national) {
    return { loading: false, error: undefined, data: undefined };
  }
  const yearData = regionData[variables.year] || regionData[defaultYear];
  const nationalData = blsData.regionData[national.regionId]
    ? blsData.regionData[national.regionId][variables.year] ||
      blsData.regionData[national.regionId][defaultYear]
    : undefined;
  if (!yearData || !nationalData) {
    return { loading: false, error: undefined, data: undefined };
  }

  const occInfo: Record<string, { majorGroupId: string; level: number }> = {};
  blsData.occupations.forEach((o) => {
    occInfo[o.socCode] = { majorGroupId: o.majorGroupId, level: o.level };
  });
  const isLevelOne = (code: string) =>
    occInfo[code] ? occInfo[code].level === 1 : code.endsWith("-0000");

  const nationalEmp: Record<string, number> = {};
  let nationalTotal = 0;
  nationalData.forEach((occ) => {
    nationalEmp[occ.socCode] = occ.totEmp;
    if (isLevelOne(occ.socCode)) nationalTotal += occ.totEmp;
  });
  const regionEmp: Record<string, number> = {};
  let regionTotal = 0;
  yearData.forEach((occ) => {
    regionEmp[occ.socCode] = occ.totEmp;
    if (isLevelOne(occ.socCode)) regionTotal += occ.totEmp;
  });

  const rcaOf = (regional: number, nationalValue: number) =>
    regionTotal > 0 && nationalTotal > 0 && nationalValue > 0
      ? regional / regionTotal / (nationalValue / nationalTotal)
      : null;

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
      rca: rcaOf(occ.totEmp, nationalEmp[occ.socCode] || 0),
    });
  });

  const clusterData: ClusterData[] = [];
  const c1Rca: ClusterRca[] = [];
  const c3Rca: ClusterRca[] = [];

  if (variables.clusters) {
    // Occupation/Job Space knowledge clusters: sum member occupations
    const agg: Record<string, { level: number; r: number; n: number }> = {};
    variables.clusters.nodes.forEach((node) => {
      [
        { id: node.continent, level: 1 },
        { id: node.country, level: 3 },
      ].forEach(({ id, level }) => {
        if (!agg[id]) agg[id] = { level, r: 0, n: 0 };
        agg[id].r += regionEmp[node.id] || 0;
        agg[id].n += nationalEmp[node.id] || 0;
      });
    });
    Object.keys(agg).forEach((id) => {
      const { level, r, n } = agg[id];
      clusterData.push({ clusterId: id, level, numEmploy: r });
      (level === 1 ? c1Rca : c3Rca).push({ clusterId: id, rca: rcaOf(r, n) });
    });
  } else {
    // SOC major groups (level-1 records)
    yearData.forEach((occ) => {
      if (isLevelOne(occ.socCode)) {
        const mgId = occInfo[occ.socCode]
          ? occInfo[occ.socCode].majorGroupId
          : occ.socCode.substring(0, 2);
        const rca = rcaOf(occ.totEmp, nationalEmp[occ.socCode] || 0);
        clusterData.push({ clusterId: mgId, level: 1, numEmploy: occ.totEmp });
        c1Rca.push({ clusterId: mgId, rca });
        c3Rca.push({ clusterId: mgId, rca });
      }
    });
  }

  const data: SuccessResponse = { clusterData, naicsData, naicsRca, c1Rca, c3Rca };
  return { loading: false, error: undefined, data };
};

const useRCAData = (_level: DigitLevel, clusters?: ClusterMembership) => {
  const cityId = useCurrentCityId();

  const { loading, error, data } = useClusterIntensityQuery({
    cityId,
    year: defaultYear,
    clusters,
  });

  return cityId !== null
    ? { loading, error, data }
    : { loading: true, error: undefined, data: undefined };
};

export default useRCAData;
