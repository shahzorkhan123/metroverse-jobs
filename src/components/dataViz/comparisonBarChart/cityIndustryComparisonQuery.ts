import { useStaticData } from "../../../dataProvider";
import {
  isValidPeerGroup,
  PeerGroup,
} from "../../../types/graphQL/graphQLTypes";
import { AggregationMode } from "../../../routing/routes";
import { defaultYear } from "../../../Utils";

export enum RegionGroup {
  World = "world",
}

interface IndustriesList {
  id: string;
  industryId: string;
  numCompany: number | null;
  numEmploy: number | null;
}

export interface SuccessResponse {
  primaryCityIndustries: IndustriesList[];
  secondaryCityIndustries: IndustriesList[];
}

interface InputVariables {
  primaryCity: number;
  comparison: number | RegionGroup | PeerGroup;
  year: number;
  aggregation: AggregationMode;
}

export const useEconomicCompositionComparisonQuery = (variables: {
  primaryCity: number;
  secondaryCity: number;
  year: number;
}) => {
  return useComparisonQuery({
    primaryCity: variables.primaryCity,
    comparison: variables.secondaryCity,
    year: variables.year,
    aggregation: AggregationMode.industries,
  });
};

export const useComparisonQuery = (input: InputVariables) => {
  const { data: blsData, loading: blsLoading } = useStaticData();

  if (blsLoading || !blsData) {
    return { loading: true, error: undefined, data: undefined };
  }

  const primaryId = input.primaryCity.toString();
  const primaryRegionData = blsData.regionData[primaryId];

  if (!primaryRegionData) {
    return { loading: false, error: undefined, data: undefined };
  }

  const primaryYearData = primaryRegionData[input.year] || primaryRegionData[defaultYear];
  if (!primaryYearData) {
    return { loading: false, error: undefined, data: undefined };
  }

  const primaryCityIndustries: IndustriesList[] = primaryYearData.map((occ) => ({
    id: occ.socCode,
    industryId: occ.socCode,
    numCompany: occ.gdp,
    numEmploy: occ.totEmp,
  }));

  let secondaryCityIndustries: IndustriesList[] = [];

  // If comparing to another specific city
  if (
    typeof input.comparison === "number" ||
    (typeof input.comparison === "string" &&
      !isValidPeerGroup(input.comparison) &&
      input.comparison !== RegionGroup.World)
  ) {
    const secondaryId = input.comparison.toString();
    const secondaryRegionData = blsData.regionData[secondaryId];
    if (secondaryRegionData) {
      const secondaryYearData =
        secondaryRegionData[input.year] || secondaryRegionData[defaultYear];
      if (secondaryYearData) {
        secondaryCityIndustries = secondaryYearData.map((occ) => ({
          id: occ.socCode,
          industryId: occ.socCode,
          numCompany: occ.gdp,
          numEmploy: occ.totEmp,
        }));
      }
    }
  }
  // For peer groups and world: use national average as proxy
  else {
    const nationalData = blsData.regionData["national_us"];
    if (nationalData) {
      const nationalYearData = nationalData[input.year] || nationalData[defaultYear];
      if (nationalYearData) {
        secondaryCityIndustries = nationalYearData.map((occ) => ({
          id: occ.socCode,
          industryId: occ.socCode,
          numCompany: occ.gdp,
          numEmploy: occ.totEmp,
        }));
      }
    }
  }

  const data: SuccessResponse = { primaryCityIndustries, secondaryCityIndustries };
  return { loading: false, error: undefined, data };
};
