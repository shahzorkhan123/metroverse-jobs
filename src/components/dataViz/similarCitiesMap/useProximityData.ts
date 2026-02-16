import useCurrentCityId from "../../../hooks/useCurrentCityId";

export interface SuccessResponse {
  cities: {
    cityId: string;
    partnerId: string;
    eucdist: number | null;
    id: string;
  }[];
  cityPartnerEucdistScale: {
    minGlobalEucdist: number;
    p20GlobalEucdist: number;
    p40GlobalEucdist: number;
    p60GlobalEucdist: number;
    p80GlobalEucdist: number;
    maxGlobalEucdist: number;
  };
}

// Stubbed: no proximity/similarity data in BLS static dataset
const useProximityData = () => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _cityId = useCurrentCityId();

  return {
    loading: false,
    error: undefined,
    data: {
      cities: [],
      cityPartnerEucdistScale: {
        minGlobalEucdist: 0,
        p20GlobalEucdist: 0,
        p40GlobalEucdist: 0,
        p60GlobalEucdist: 0,
        p80GlobalEucdist: 0,
        maxGlobalEucdist: 0,
      },
    } as SuccessResponse,
  };
};

export default useProximityData;
