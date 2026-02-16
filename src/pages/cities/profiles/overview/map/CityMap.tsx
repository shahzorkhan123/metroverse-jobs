import React from "react";
import styled from "styled-components/macro";
import {
  backgroundMedium,
  baseColor,
} from "../../../../../styling/styleUtils";

const Placeholder = styled.div`
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: ${backgroundMedium};
  color: ${baseColor};
  font-size: 0.9rem;
  text-align: center;
  padding: 2rem;
`;

export interface BoundsConfig {
  bounds: [[number, number], [number, number]];
  padding: { top: number; left: number; right: number; bottom: number };
}

interface Props {
  loading: boolean;
  error: any;
  data: any;
  currentCityId: string | null;
  fitBounds: BoundsConfig;
}

// Replaced Mapbox map with placeholder for static BLS site
const CityMap = (_props: Props) => {
  return (
    <Placeholder>
      Region overview — map visualization not available in static mode.
    </Placeholder>
  );
};

export default CityMap;
