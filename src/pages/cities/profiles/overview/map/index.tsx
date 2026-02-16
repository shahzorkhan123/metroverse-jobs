import React from "react";
import styled from "styled-components/macro";
import useCurrentCityId from "../../../../../hooks/useCurrentCityId";
import CityMap, { BoundsConfig } from "./CityMap";
import {
  backgroundMedium,
} from "../../../../../styling/styleUtils";

const Root = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
  background-color: ${backgroundMedium};
`;

const MapRoot = () => {
  const currentCityId = useCurrentCityId();

  const fitBounds: BoundsConfig = {
    bounds: [[0, 0], [0, 0]],
    padding: { top: 0, bottom: 0, left: 0, right: 0 },
  };

  return (
    <Root>
      <CityMap
        loading={false}
        error={undefined}
        data={undefined}
        currentCityId={currentCityId}
        fitBounds={fitBounds}
      />
    </Root>
  );
};

export default MapRoot;
