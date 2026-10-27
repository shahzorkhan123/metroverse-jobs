/** TypeScript interfaces for the static BLS data JSON files */

export interface BLSRegion {
  regionId: string;
  name: string;
  regionType: 'National' | 'State' | 'Metro';
}

export interface BLSOccupation {
  socCode: string;
  name: string;
  level: number;
  parentCode: string | null;
  majorGroupId: string;
  majorGroupName: string;
}

export interface BLSMajorGroup {
  groupId: string;
  name: string;
  color: string;
}

export interface BLSRegionOccupation {
  socCode: string;
  totEmp: number;
  gdp: number;
  aMean: number;
  complexity: number;
}

export interface BLSAggregateOccupation {
  totalEmploy: number;
  avgWage: number;
  avgComplexity: number;
}

export interface BLSMinMaxStats {
  minWage: number;
  maxWage: number;
  medianWage: number;
  minComplexity: number;
  maxComplexity: number;
  medianComplexity: number;
}

export interface BLSAggregates {
  byOccupation: { [socCode: string]: BLSAggregateOccupation };
  minMaxStats: BLSMinMaxStats;
}

export interface BLSData {
  metadata: {
    lastUpdated: string;
    years: number[];
    source: string;
    country?: string;
    maxLevel?: number;
    level?: number;
    occupationMap?: {
      [socCode: string]: {
        name: string;
        level: number;
        parentCode: string | null;
        majorGroupId: string;
        majorGroupName: string;
      };
    };
  };
  regions: BLSRegion[];
  occupations: BLSOccupation[];
  majorGroups: BLSMajorGroup[];
  regionData: {
    [regionId: string]: {
      [year: string]: BLSRegionOccupation[];
    };
  };
  aggregates: {
    [year: string]: BLSAggregates;
  };
}

/** Per-country metadata (terminology, levels, colors, hierarchy) */
export interface CountryMetadata {
  classificationSystem: string;
  currency: string;
  currencySymbol: string;
  terminology: Record<string, string>;
  levels: Record<string, { name: string }>;
  maxLevel: number;
  regionTypes: { id: string; pluralName: string }[];
  majorGroups: { id: string; name: string; color: string }[];
  hierarchyRules: { strategy: string };
  stateAbbreviations?: Record<string, string>;
  /** Local currency units per 1 USD, keyed by dataset year (for USD equivalents) */
  usdExchangeRates?: Record<string, number>;
}

/** Time-series data file structure */
export interface TimeSeriesFile {
  metadata: {
    source: string;
    country: string;
    years: number[];
    hasGdp: boolean;
  };
  groups: { id: string; name: string; color?: string }[];
  regions: { regionId: string; name: string; regionType: string }[];
  data: {
    [regionId: string]: {
      [groupId: string]: {
        emp: (number | null)[];
        gdp?: (number | null)[];
      };
    };
  };
}

/** SOC 2018 levels used as divisions, coarsest first */
export type SocLevel = 'high' | 'intermediate' | 'major' | 'minor';
export const socLevels: SocLevel[] = ['high', 'intermediate', 'major', 'minor'];

/** Where a SOC group concentrates and what it is made of */
export interface SpaceClusterProfile {
  /** Share of national employment, % */
  empShare: number;
  meanPci: number | null;
  /** Metros (>= 100k jobs) with the highest RCA in the group */
  topRegions: { id: string; name: string; rca: number }[];
  /** Largest occupations by national employment */
  topOccupations: { id: string; name: string }[];
}

/** SOC group hull in an Occupation/Job Space layout */
export interface SpaceCluster {
  clusterId: string;
  clusterCode: number;
  name: string;
  /** Group id one SOC level up (null for high-level groups) */
  parentId: string | null;
  center: number[];
  polygon: number[][];
  color: string;
  size: number;
  profile: SpaceClusterProfile;
}

/** Occupation Space / Job Space layout (space-{country}-{year}-{kind}.json) */
export interface SpaceFile {
  kind: 'occupation' | 'job';
  nodes: {
    id: string;
    x: number;
    y: number;
    /** SOC group id at each level, e.g. {high: "h1", ..., minor: "n11-1000"} */
    groups: { [level in SocLevel]: string };
    /** Top-10 most proximate occupations (phi) */
    edges: { trg: string; proximity: number }[];
  }[];
  /** Drawn backbone: maximum spanning tree + top-k links, [source, target, phi] */
  links: [string, string, number][];
  clusters: { levels: { [level in SocLevel]: SpaceCluster[] } };
  stats: {
    nNodes: number;
    nLinks: number;
    avgDegree: number;
    topK: number;
    phiCutoff: number;
    layout: string;
    phiFidelity: number;
    nGroups: { [level in SocLevel]: number };
  };
}

/** Complexity measures (complexity-{country}-{year}.json) */
export interface ComplexityFile {
  year: number;
  /** Occupation Complexity Index (metro co-location, method of reflections) */
  pci: { [socCode: string]: number };
  /** Job Complexity Index (wage-seeded reflections over O*NET tasks), in $ */
  jci: { [socCode: string]: number };
  /** Region complexity (metros only) */
  eci: { [regionId: string]: number };
  diversity: { [regionId: string]: number };
  ubiquity: { [socCode: string]: number };
  tciTop: { id: string; name: string; tci: number }[];
  stats: {
    corrPciLogWage: number;
    corrJciLogWage: number;
    nPci: number;
    nJci: number;
    nRegionsEci: number;
    nDwa: number;
  };
}

/** Meta catalog file (bls-data.json) */
export interface BLSMetaCatalog {
  datasets: {
    country: string;
    year: number;
    file: string;
    levels: number[];
  }[];
  levelFiles: {
    [countryYear: string]: {
      [level: string]: string;
    };
  };
  countries: { code: string; name: string; flagEmoji?: string }[];
  yearsByCountry: { [countryCode: string]: number[] };
  countryMetadata: { [countryCode: string]: CountryMetadata };
  timeseriesFiles?: {
    [country: string]: {
      [source: string]: { base: string; metro?: string };
    };
  };
  spaceFiles?: {
    [country: string]: {
      [year: string]: { occupation: string; job: string; complexity: string };
    };
  };
  lastUpdated: string;
}
