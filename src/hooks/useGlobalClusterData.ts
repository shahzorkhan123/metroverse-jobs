import { useStaticData } from '../dataProvider';
import { Datum as SearchDatum } from 'react-panel-search';

/**
 * Adapter hook: returns SOC major groups as "clusters".
 *
 * Key mapping:
 *   clusterId -> majorGroupId
 *   clusterIdTopParent -> majorGroupId (self, since flat)
 *   name -> majorGroupName
 */

interface Cluster {
  clusterId: string;
  parentId: number | null;
  clusterIdTopParent: number | null;
  level: number | null;
  name: string | null;
  tradable: boolean;
  id: string;
}

interface SuccessResponse {
  clusters: Cluster[];
}

interface ClusterMap {
  [id: string]: Cluster;
}

const useGlobalClusterData = () => {
  const { data: blsData, loading, error } = useStaticData();

  if (!blsData) {
    return { loading, error, data: undefined };
  }

  const clusters: Cluster[] = blsData.majorGroups.map((mg) => ({
    clusterId: mg.groupId,
    parentId: null,
    clusterIdTopParent: parseInt(mg.groupId, 10),
    level: 1,
    name: mg.name,
    tradable: true,
    id: mg.groupId,
  }));

  const data: SuccessResponse = { clusters };
  return { loading: false, error: undefined, data };
};

const clusterDataToHierarchicalTreeData = (
  data: SuccessResponse | undefined,
) => {
  const response: SearchDatum[] = [];
  if (data !== undefined) {
    const { clusters } = data;
    clusters.forEach(({ clusterId, name, level }) => {
      if (name !== null && level !== null) {
        response.push({
          id: clusterId,
          title: name,
          level,
          parent_id: null,
        });
      }
    });
  }
  return response;
};

export const useGlobalClusterHierarchicalTreeData = () => {
  const { loading, error, data: responseData } = useGlobalClusterData();
  const data = clusterDataToHierarchicalTreeData(responseData);
  return { loading, error, data };
};

const clusterDataToMap = (
  data: SuccessResponse | undefined,
) => {
  const response: ClusterMap = {};
  if (data !== undefined) {
    const { clusters } = data;
    clusters.forEach((cluster) => {
      response[cluster.clusterId] = cluster;
    });
  }
  return response;
};

interface Options {
  skipLevel2?: boolean;
}

export const useGlobalClusterMap = (_options?: Options) => {
  const { loading, error, data: responseData } = useGlobalClusterData();
  const data = clusterDataToMap(responseData);
  return { loading, error, data };
};

export default useGlobalClusterData;
