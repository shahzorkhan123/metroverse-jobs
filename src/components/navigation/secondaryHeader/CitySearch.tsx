import React from "react";
import styled from "styled-components/macro";
import {
  secondaryFont,
  lightBaseColor,
} from "../../../styling/styleUtils";
import { useStaticData } from "../../../dataProvider";
import useCurrentCityId from "../../../hooks/useCurrentCityId";
import { useHistory, matchPath } from "react-router-dom";
import { CityRoutes, cityIdParam } from "../../../routing/routes";
import { ValueOfCityRoutes, createRoute } from "../../../routing/Utils";
import queryString from "query-string";
import useQueryParams from "../../../hooks/useQueryParams";

const Root = styled.div`
  display: flex;
  gap: 0.5rem;
  align-items: center;
  height: 100%;

  @media (max-width: 600px) {
    flex-direction: column;
    align-items: stretch;
    gap: 0.3rem;
  }
`;

const StyledSelect = styled.select`
  font-family: ${secondaryFont};
  font-size: 0.7rem;
  text-transform: uppercase;
  background-color: #fff;
  border: solid 1px ${lightBaseColor};
  padding: 0.35rem 1.5rem 0.35rem 0.5rem;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23333' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 0.3rem center;
  background-size: 0.8rem;
  min-width: 0;

  &:focus {
    outline: none;
    border-color: #333;
  }

  @media (max-width: 600px) {
    width: 100%;
  }
`;

const CountrySelect = styled(StyledSelect)`
  width: 130px;

  @media (max-width: 600px) {
    width: 100%;
  }
`;

const YearSelect = styled(StyledSelect)`
  width: 80px;

  @media (max-width: 600px) {
    width: 100%;
  }
`;

const RegionSelect = styled(StyledSelect)`
  width: clamp(200px, 30vw, 400px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  @media (max-width: 600px) {
    width: 100%;
  }
`;

const Label = styled.span`
  font-family: ${secondaryFont};
  font-size: 0.6rem;
  text-transform: uppercase;
  color: #666;
  letter-spacing: 0.05em;

  @media (max-width: 600px) {
    display: none;
  }
`;

const CitySearch = () => {
  const { data: blsData, loading } = useStaticData();
  const cityId = useCurrentCityId();
  const history = useHistory();
  const params = useQueryParams();

  if (loading || !blsData) {
    return <Root />;
  }

  const years = blsData.metadata.years;
  const currentYear = params.year || years[years.length - 1]?.toString() || "2024";

  // Group regions by type
  const nationals = blsData.regions
    .filter((r) => r.regionType === "National")
    .sort((a, b) => a.name.localeCompare(b.name));
  const metros = blsData.regions
    .filter((r) => r.regionType === "Metro")
    .sort((a, b) => a.name.localeCompare(b.name));
  const states = blsData.regions
    .filter((r) => r.regionType === "State")
    .sort((a, b) => a.name.localeCompare(b.name));

  const onRegionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const regionId = e.target.value;
    Object.entries(CityRoutes).forEach(([_key, value]) => {
      const match = matchPath<{ [cityIdParam]: string }>(
        history.location.pathname,
        value,
      );
      if (match && match.isExact && match.path) {
        history.push(
          createRoute.city(
            match.path as ValueOfCityRoutes,
            regionId,
          ) + history.location.search,
        );
      }
    });
  };

  const onYearChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const year = e.target.value;
    const { year: _oldYear, ...otherParams } = params;
    const query = queryString.stringify({ ...otherParams, year });
    history.push(history.location.pathname + (query ? "?" + query : ""));
  };

  return (
    <Root>
      <Label>Country</Label>
      <CountrySelect value="us" onChange={() => {}}>
        <option value="us">United States</option>
      </CountrySelect>

      <Label>Year</Label>
      <YearSelect value={currentYear} onChange={onYearChange}>
        {years.map((y) => (
          <option key={y} value={y.toString()}>
            {y}
          </option>
        ))}
      </YearSelect>

      <Label>Region</Label>
      <RegionSelect value={cityId || ""} onChange={onRegionChange}>
        {nationals.length > 0 && (
          <optgroup label="National">
            {nationals.map((r) => (
              <option key={r.regionId} value={r.regionId}>
                {r.name}
              </option>
            ))}
          </optgroup>
        )}
        {states.length > 0 && (
          <optgroup label="States">
            {states.map((r) => (
              <option key={r.regionId} value={r.regionId}>
                {r.name}
              </option>
            ))}
          </optgroup>
        )}
        {metros.length > 0 && (
          <optgroup label="Metropolitan Areas">
            {metros.map((r) => (
              <option key={r.regionId} value={r.regionId}>
                {r.name}
              </option>
            ))}
          </optgroup>
        )}
      </RegionSelect>
    </Root>
  );
};

export default CitySearch;
