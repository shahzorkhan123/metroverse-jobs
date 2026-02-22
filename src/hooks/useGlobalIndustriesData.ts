import { useStaticData } from '../dataProvider';
import { Datum as SearchDatum } from 'react-panel-search';

/**
 * Adapter hook: returns SOC occupations in the same shape as the
 * original NAICS industries data.
 *
 * Key mapping:
 *   naicsId -> socCode
 *   naicsIdTopParent -> majorGroupId (as number)
 *   code -> socCode
 *   parentId -> null (flat structure for now)
 *   tradable -> true (all occupations)
 */

interface IndustryDatum {
  id: string;
  naicsId: string;   // actually socCode
  code: string;      // socCode
  name: string | null;
  level: number | null;
  parentId: number | null;
  parentCode: string | null;
  naicsIdTopParent: number;  // majorGroupId as number
  tradable: boolean;
}

interface SuccessResponse {
  industries: IndustryDatum[];
}

interface IndustryMap {
  [id: string]: IndustryDatum;
}

const useGlobalIndustriesData = () => {
  const { data: blsData, loading, error } = useStaticData();

  if (!blsData) {
    return { loading, error, data: undefined };
  }

  const industries: IndustryDatum[] = blsData.occupations.map((occ) => ({
    id: occ.socCode,
    naicsId: occ.socCode,
    code: occ.socCode,
    name: occ.name,
    level: occ.level,
    parentId: occ.parentCode ? parseInt(occ.parentCode.substring(0, 2), 10) : null,
    parentCode: occ.parentCode,
    naicsIdTopParent: parseInt(occ.majorGroupId, 10),
    tradable: true,
  }));

  const data: SuccessResponse = { industries };
  return { loading: false, error: undefined, data };
};

const industryDataToHierarchicalTreeData = (
  data: SuccessResponse | undefined,
) => {
  const response: SearchDatum[] = [];
  if (data !== undefined) {
    const { industries } = data;
    industries.forEach(({ naicsId, name, level, parentId }) => {
      if (name !== null && level !== null) {
        response.push({
          id: naicsId,
          title: name,
          level,
          parent_id: parentId === null ? null : parentId.toString(),
        });
      }
    });
  }
  return response;
};

export const useGlobalIndustryHierarchicalTreeData = () => {
  const { loading, error, data: responseData } = useGlobalIndustriesData();
  const data = industryDataToHierarchicalTreeData(responseData);
  return { loading, error, data };
};

const industryDataToMap = (data: SuccessResponse | undefined) => {
  const response: IndustryMap = {};
  if (data !== undefined) {
    const { industries } = data;
    industries.forEach((industry) => {
      response[industry.naicsId] = industry;
    });
  }
  return response;
};

export const useGlobalIndustryMap = () => {
  const { loading, error, data: responseData } = useGlobalIndustriesData();
  const data = industryDataToMap(responseData);
  return { loading, error, data };
};

export default useGlobalIndustriesData;
