import React from "react";
import styled from "styled-components/macro";
import {
  backgroundMedium,
  baseColor,
  primaryColor,
  secondaryFont,
} from "../../../../../styling/styleUtils";
import useCurrentCity from "../../../../../hooks/useCurrentCity";
import { useStaticData } from "../../../../../dataProvider";
import { formatRegionDisplayName } from "../../../../../hooks/useGlobalLocationData";

const Root = styled.div`
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 0.5rem;
  padding: 1rem;
  box-sizing: border-box;
`;

const Header = styled.div`
  width: 100%;
  color: ${baseColor};
  font-family: ${secondaryFont};
  font-size: 0.9rem;
`;

const Subtitle = styled.div`
  margin-top: 0.2rem;
  color: ${baseColor};
  opacity: 0.8;
  font-size: 0.8rem;
`;

const LocatorBox = styled.div`
  position: relative;
  width: 100%;
  min-height: 220px;
  display: flex;
  border: 1px solid rgba(0, 0, 0, 0.15);
  background-color: ${backgroundMedium};
  background-image:
    repeating-linear-gradient(
      to right,
      rgba(0, 0, 0, 0.05) 0,
      rgba(0, 0, 0, 0.05) 1px,
      transparent 1px,
      transparent 10%
    ),
    repeating-linear-gradient(
      to bottom,
      rgba(0, 0, 0, 0.05) 0,
      rgba(0, 0, 0, 0.05) 1px,
      transparent 1px,
      transparent 16.666%
    );
`;

const Marker = styled.div<{ x: number; y: number }>`
  position: absolute;
  left: ${(props) => props.x}%;
  top: ${(props) => props.y}%;
  transform: translate(-50%, -50%);
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 1000px;
  background: ${primaryColor};
  box-shadow: 0 0 0 4px rgba(42, 127, 98, 0.18);
`;

const MarkerLabel = styled.div<{ x: number; y: number }>`
  position: absolute;
  left: ${(props) => props.x}%;
  top: calc(${(props) => props.y}% + 0.8rem);
  transform: translateX(-50%);
  white-space: nowrap;
  color: ${baseColor};
  font-size: 0.75rem;
  font-family: ${secondaryFont};
`;

const Footer = styled.div`
  color: ${baseColor};
  opacity: 0.8;
  font-size: 0.9rem;
  line-height: 1.25;
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

const countryCenters: Record<string, { lat: number; lon: number }> = {
  us: { lat: 39.5, lon: -98.35 },
  in: { lat: 22.9, lon: 79.3 },
};

const toPosition = (lat: number, lon: number) => {
  const x = ((lon + 180) / 360) * 100;
  const y = ((90 - lat) / 180) * 100;
  return { x, y };
};

const CityMap = (_props: Props) => {
  const { city } = useCurrentCity();
  const { selectedCountry } = useStaticData();

  const regionLabel = city
    ? formatRegionDisplayName(city.name, city.countryId)
    : "Selected Region";
  const regionTypeLabel = city ? city.countryId : "Region";
  const center = countryCenters[selectedCountry] || countryCenters.us;
  const pos = toPosition(center.lat, center.lon);

  return (
    <Root>
      <Header>
        {regionLabel}
        <Subtitle>{regionTypeLabel}</Subtitle>
      </Header>
      <LocatorBox>
        <Marker x={pos.x} y={pos.y} />
        <MarkerLabel x={pos.x} y={pos.y}>
          Approximate country location
        </MarkerLabel>
      </LocatorBox>
      <Footer>
        Static mode: region overview uses country-level centroid markers.
      </Footer>
    </Root>
  );
};

export default CityMap;
