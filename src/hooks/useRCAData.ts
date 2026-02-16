import { useStaticData } from "../dataProvider";
import {
  DigitLevel,
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

interface NaicsDensity {
  naicsId: string;
  densityCompany: number | null;
  densityEmploy: number | null;
}

interface NaicsData {
  naicsId: string;
  numCompany: number | null;
  numEmploy: number | null;
}

interface NaicsRca {
  naicsId: string;
  comparableIndustry: number | null;
  rca: number | null;
}

export interface SuccessResponse {
  naicsDensity: NaicsDensity[];
  naicsRca: NaicsRca[];
  naicsData: NaicsData[];
}

const useRCAData = (_level: DigitLevel) => {
  const cityId = useCurrentCityId();
  const { data: blsData, loading: blsLoading } = useStaticData();

  const { composition_type } = useQueryParams();

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

  const naicsData: NaicsData[] = [];
  const naicsRca: NaicsRca[] = [];
  const naicsDensity: NaicsDensity[] = [];

  yearData.forEach((occ) => {
    naicsData.push({
      naicsId: occ.socCode,
      numCompany: occ.gdp,
      numEmploy: occ.totEmp,
    });
    naicsRca.push({
      naicsId: occ.socCode,
      rca: 1.0,
      comparableIndustry: null,
    });
    naicsDensity.push({
      naicsId: occ.socCode,
      densityCompany: null,
      densityEmploy: null,
    });
  });

  const data: SuccessResponse = { naicsDensity, naicsRca, naicsData };
  return { loading: false, error: undefined, data };
};

export default useRCAData;
