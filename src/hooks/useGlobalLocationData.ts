import { useStaticData } from '../dataProvider';
import { Datum as SearchDatum } from 'react-panel-search';
import { DataFlagType } from '../types/graphQL/graphQLTypes';

/**
 * Adapter hook: replaces Apollo GraphQL query with static BLS data.
 * Returns regions as "cities" and regionTypes as "countries" to match
 * the original Metroverse data shape.
 */

interface CityDatum {
  cityId: string;  // regionId
  name: string;
  countryId: string;  // regionType slug
  id: string;  // regionId
  nameList: string[] | null;
  centroidLat: number | null;
  centroidLon: number | null;
  population: number | null;
  gdppc: number | null;
  incomeClass: null;
  region: null;
  regionPopRank: null;
  regionGdppcRank: null;
  dataFlag: DataFlagType;
}

interface CountryDatum {
  countryId: string;  // regionType slug
  code: string;
  nameShortEn: string;  // regionType display name
  id: string;
}

interface RegionDatum {
  regionId: string;
  regionName: string;
}

interface SuccessResponse {
  countries: CountryDatum[];
  cities: CityDatum[];
  regions: RegionDatum[];
}

const regionTypeLabels: Record<string, string> = {
  'National': 'National',
  'State': 'States',
  'Metro': 'Metropolitan Areas',
};

const useGlobalLocationData = () => {
  const { data: blsData, loading, error } = useStaticData();

  if (!blsData) {
    return { loading, error, data: undefined };
  }

  // Map regionTypes to "countries"
  const regionTypes = Array.from(new Set(blsData.regions.map((r) => r.regionType)));
  const countries: CountryDatum[] = regionTypes.map((rt) => ({
    countryId: rt,
    code: rt.toLowerCase(),
    nameShortEn: regionTypeLabels[rt] || rt,
    id: rt,
  }));

  // Map regions to "cities"
  const cities: CityDatum[] = blsData.regions.map((r) => ({
    cityId: r.regionId,
    name: r.name,
    countryId: r.regionType,
    id: r.regionId,
    nameList: null,
    centroidLat: null,
    centroidLon: null,
    population: null,
    gdppc: null,
    incomeClass: null,
    region: null,
    regionPopRank: null,
    regionGdppcRank: null,
    dataFlag: DataFlagType.GREEN,
  }));

  // No sub-regions in BLS
  const regions: RegionDatum[] = [];

  const data: SuccessResponse = { countries, cities, regions };
  return { loading: false, error: undefined, data };
};

const getCountryStringId = (id: number | string | null) => `country-${id}`;

export const locationDataToHierarchicalTreeData = (
  data: SuccessResponse | undefined,
) => {
  const response: SearchDatum[] = [];
  if (data !== undefined) {
    const { cities, countries } = data;
    response.push(
      ...countries.map(({ nameShortEn, countryId }) => ({
        id: getCountryStringId(countryId),
        title: nameShortEn !== null ? nameShortEn : 'Unknown',
        parent_id: null,
        level: '0',
      })),
      ...cities.map(({ cityId: id, name, countryId }) => {
        return {
          id,
          title: name !== null ? name : 'Unknown Region ' + id,
          parent_id: getCountryStringId(countryId),
          level: '1',
        };
      }),
    );
  }
  return response;
};

export const getPopulationScale = () => {
  // Stub - no population data for BLS regions
  return () => 5;
};

export const getGdpPppScale = () => {
  // Stub - no GDP PPP data for BLS regions
  return () => 5;
};

export const useGlobalLocationHierarchicalTreeData = () => {
  const { loading, error, data: responseData } = useGlobalLocationData();
  const data = locationDataToHierarchicalTreeData(responseData);
  return { loading, error, data };
};

export default useGlobalLocationData;
