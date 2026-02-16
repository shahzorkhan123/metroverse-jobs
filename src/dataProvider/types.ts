/** TypeScript interfaces for the static BLS data JSON (bls-data.json) */

export interface BLSRegion {
  regionId: string;
  name: string;
  regionType: 'National' | 'State' | 'Metro';
}

export interface BLSOccupation {
  socCode: string;
  name: string;
  level: number;
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
