import { useEffect, useMemo } from "react";
import { scaleLinear } from "d3-scale";
import {
  wageColorRange,
  educationColorRange,
} from "../../../../styling/styleUtils";
import useSectorMap from "../../../../hooks/useSectorMap";
import { useStaticData } from "../../../../dataProvider";
import {
  useSpaceLayout,
  useComplexityData,
  useCurrentDivisionLevel,
} from "../../../../hooks/useSpaceData";
import { SpaceType } from "../../../../routing/routes";
import {
  SpaceClusterProfile,
  socLevels,
} from "../../../../dataProvider/types";
import { defaultYear } from "../../../../Utils";

interface ContinentCluster {
  center: number[];
  color: string;
  clusterCode: number;
  clusterId: string;
  name: string;
  polygon: number[][];
  numEmploy?: number;
  shareEmploy?: number;
  size?: number;
  profile?: SpaceClusterProfile;
}

interface CountryCluster extends ContinentCluster {
  continent: string;
}

interface Clusters {
  continents: ContinentCluster[];
  countries: CountryCluster[];
}

interface Edge {
  trg: string;
  proximity: number;
}

interface Node {
  id: string;
  name: string;
  code: string;
  industryColor: string;
  color: string;
  sectorName: string;
  continent: string;
  country: string;
  edges: Edge[];
  x: number;
  y: number;
  rca?: number;
  radius?: number;
  globalSumNumCompany: number;
  globalSumNumEmploy: number;
  /** Complexity used by ColorBy.education (= PCI scaled 0-1) */
  yearsEducation: number;
  /** National mean annual wage */
  hourlyWage: number;
  pci: number | null;
  jci: number | null;
  educationColor: string;
  wageColor: string;
  pciColor: string;
  jciColor: string;
}

export interface LayoutData {
  kind: SpaceType;
  clusters: Clusters;
  nodes: Node[];
  links: [string, string, number][];
  global: {
    companySizeByScale: (value: number) => number;
    employSizeByScale: (value: number) => number;
  };
}

interface Output {
  loading: boolean;
  error: any;
  data: LayoutData | undefined;
}

export const lowIntensityNodeColor = "#dddddd";

const median = (values: number[]) => {
  const sorted = values.slice().sort((a, b) => a - b);
  return sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
};

const divergingScale = (values: number[], range: string[]) => {
  const scale = scaleLinear<string>()
    .domain([Math.min(...values), median(values), Math.max(...values)])
    .range(range)
    .clamp(true);
  return (value: number) => scale(value) as string;
};

/**
 * Occupation Space / Job Space layout joined to SOC occupation data.
 *
 * Nodes and cluster hulls come from space-{country}-{year}-{kind}.json
 * (scripts/pipeline/compute_space.py); names, colours and national totals
 * come from the level-4 occupation data, which is lazy-loaded here.
 */
const useLayoutData = (kind?: SpaceType): Output => {
  const sectorMap = useSectorMap();
  const sectorKey = sectorMap.map((s) => s.id + s.color).join("|");
  const {
    data: blsData,
    loadLevel,
    loadedLevels,
    maxDigitLevel,
  } = useStaticData();
  const space = useSpaceLayout(kind);
  const complexity = useComplexityData();
  const division = useCurrentDivisionLevel();

  useEffect(() => {
    for (let lvl = 3; lvl <= Math.min(4, maxDigitLevel); lvl++) {
      if (!loadedLevels.includes(lvl)) {
        loadLevel(lvl);
      }
    }
  }, [loadLevel, loadedLevels, maxDigitLevel]);

  const levelFourLoaded = loadedLevels.includes(4);

  const data = useMemo((): LayoutData | undefined => {
    if (!space.data || !complexity.data || !blsData || !levelFourLoaded) {
      return undefined;
    }
    const colorBySector: { [id: string]: { color: string; name: string } } =
      {};
    sectorMap.forEach((s) => (colorBySector[s.id] = s));

    const occupations: {
      [code: string]: { name: string; majorGroupId: string };
    } = {};
    blsData.occupations.forEach((o) => {
      occupations[o.socCode] = { name: o.name, majorGroupId: o.majorGroupId };
    });

    const nationalId = blsData.regions.find(
      (r) => r.regionType === "National",
    );
    const nationalRecords =
      nationalId && blsData.regionData[nationalId.regionId]
        ? blsData.regionData[nationalId.regionId][defaultYear] || []
        : [];
    const nationalBySoc: { [code: string]: { emp: number; gdp: number; wage: number } } = {};
    nationalRecords.forEach((r) => {
      nationalBySoc[r.socCode] = { emp: r.totEmp, gdp: r.gdp, wage: r.aMean };
    });

    const { pci, jci } = complexity.data;
    const nodeCodes = space.data.nodes.map((n) => n.id);
    const wages = nodeCodes
      .map((c) => (nationalBySoc[c] ? nationalBySoc[c].wage : 0))
      .filter((v) => v > 0);
    const pcis = nodeCodes.filter((c) => pci[c] !== undefined).map((c) => pci[c]);
    const jcis = nodeCodes.filter((c) => jci[c] !== undefined).map((c) => jci[c]);
    const wageColorScale = divergingScale(wages, wageColorRange);
    const pciColorScale = divergingScale(pcis, educationColorRange);
    const jciColorScale = divergingScale(jcis, educationColorRange);
    const pciMin = Math.min(...pcis);
    const pciMax = Math.max(...pcis);

    const emps = nodeCodes.map((c) => (nationalBySoc[c] ? nationalBySoc[c].emp : 0));
    const gdps = nodeCodes.map((c) => (nationalBySoc[c] ? nationalBySoc[c].gdp : 0));
    const employSizeByScale = scaleLinear()
      .domain([Math.min(...emps), Math.max(...emps)])
      .range([3, 15]) as (val: number) => number;
    const companySizeByScale = scaleLinear()
      .domain([Math.min(...gdps), Math.max(...gdps)])
      .range([3, 15]) as (val: number) => number;

    // Division level d: SOC level d-1 is drawn as continents, level d as countries
    const outerLevel = socLevels[parseInt(division, 10) - 1];
    const innerLevel = socLevels[parseInt(division, 10)];

    const nodes: Node[] = space.data.nodes.map((n) => {
      const occ = occupations[n.id];
      const majorGroupId = occ ? occ.majorGroupId : n.id.substring(0, 2);
      const sector = colorBySector[majorGroupId];
      const sectorColor = sector ? sector.color : lowIntensityNodeColor;
      const nat = nationalBySoc[n.id];
      const nodePci = pci[n.id] !== undefined ? pci[n.id] : null;
      const nodeJci = jci[n.id] !== undefined ? jci[n.id] : null;
      return {
        id: n.id,
        x: n.x,
        y: n.y,
        edges: n.edges,
        continent: n.groups[outerLevel],
        country: n.groups[innerLevel],
        name: occ ? occ.name : n.id,
        code: n.id,
        industryColor: sectorColor,
        color: sectorColor,
        sectorName: sector ? sector.name : "",
        globalSumNumEmploy: nat ? nat.emp : 0,
        globalSumNumCompany: nat ? nat.gdp : 0,
        hourlyWage: nat ? nat.wage : 0,
        yearsEducation:
          nodePci !== null && pciMax > pciMin
            ? (nodePci - pciMin) / (pciMax - pciMin)
            : 0,
        pci: nodePci,
        jci: nodeJci,
        wageColor: nat ? wageColorScale(nat.wage) : lowIntensityNodeColor,
        pciColor: nodePci !== null ? pciColorScale(nodePci) : lowIntensityNodeColor,
        educationColor:
          nodePci !== null ? pciColorScale(nodePci) : lowIntensityNodeColor,
        jciColor: nodeJci !== null ? jciColorScale(nodeJci) : lowIntensityNodeColor,
      };
    });

    return {
      kind: space.data.kind as SpaceType,
      clusters: {
        continents: space.data.clusters.levels[outerLevel].map((c) => ({
          ...c,
        })),
        countries: space.data.clusters.levels[innerLevel].map((c) => ({
          ...c,
          continent: c.parentId as string,
        })),
      },
      nodes,
      links: space.data.links,
      global: { companySizeByScale, employSizeByScale },
    };
    // sectorKey stands in for sectorMap, which is a new array every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [space.data, complexity.data, blsData, levelFourLoaded, sectorKey, division]);

  const error = space.error || complexity.error;
  return {
    loading: !data && !error,
    error,
    data,
  };
};

export default useLayoutData;
