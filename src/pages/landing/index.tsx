import React, { useCallback } from "react";
import styled from "styled-components/macro";
import {
  secondaryFont,
  primaryColor,
  secondaryColor,
} from "../../styling/styleUtils";
import Heading from "./Heading";
import { ExtendedSearchDatum } from "./Utils";
import { useHistory } from "react-router-dom";
import { Routes } from "../../routing/routes";
import useGlobalLocationData, {
  locationDataToHierarchicalTreeData,
} from "../../hooks/useGlobalLocationData";
import SimpleLoader from "../../components/transitionStateComponents/SimpleLoader";
import SimpleError from "../../components/transitionStateComponents/SimpleError";
import SearchBar from "./SearchBar";
import useFluent from "../../hooks/useFluent";

const Root = styled.div`
  width: 100vw;
  height: 100vh;
  position: relative;
  background-color: #08111e;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const CenterPanel = styled.div`
  width: 90%;
  max-width: 600px;
  padding: 2rem;
`;

const SearchContainer = styled.div`
  width: 100%;
  margin: 1.5rem auto 0;
  font-family: ${secondaryFont};

  .react-panel-search-search-bar-input,
  button {
    font-family: ${secondaryFont};
  }

  .react-panel-search-search-bar-input {
    text-transform: uppercase;
    font-size: 0.85rem;
    background-color: rgba(0, 0, 0, 0.85);
    color: #fff;
    border: solid 1px #fff;
    padding-top: 1rem;
    padding-bottom: 1rem;
    padding-right: 3rem;
    box-shadow: none;
    outline: none;

    &::placeholder {
      color: #fff;
    }
    &:focus::placeholder {
      color: rgba(0, 0, 0, 0);
    }
  }

  .react-panel-search-search-bar-dropdown-arrow {
    background-color: transparent;
  }
  .react-panel-search-current-tier-breadcrumb-outer,
  .react-panel-search-next-button,
  .react-panel-search-search-bar-dropdown-arrow {
    svg polyline {
      stroke: #fff;
    }
  }

  .react-panel-search-search-bar-clear-button {
    background-color: transparent;
    color: #fff;
  }

  .react-panel-search-search-bar-search-icon {
    svg path {
      fill: #fff;
    }
  }

  .react-panel-search-search-results {
    background-color: rgba(0, 0, 0, 0.85);
    border: solid 1px #fff;

    ::-webkit-scrollbar-thumb {
      background-color: rgba(255, 255, 255, 0.3);
    }
    ::-webkit-scrollbar-track {
      background-color: rgba(255, 255, 255, 0.1);
    }
  }

  .react-panel-search-current-tier-title,
  .react-panel-search-current-tier-breadcrumb-outer {
    color: #fff;
    border-color: ${primaryColor};
  }

  .react-panel-search-current-tier-breadcrumb-outer:hover {
    background-color: rgba(255, 255, 255, 0.35);
  }

  .react-panel-search-list-item {
    background-color: transparent;
    color: #fff;
    &:hover {
      background-color: rgba(255, 255, 255, 0.35);
    }
  }

  .react-panel-search-highlighted-item {
    background-color: rgba(255, 255, 255, 0.35);
  }

  .react-panel-search-search-results:hover {
    .react-panel-search-highlighted-item:not(:hover) {
      background-color: transparent;
    }
  }

  .react-panel-search-list-item-container {
    strong {
      color: ${primaryColor};
    }
  }

  .react-panel-search-list-item-container.react-panel-search-list-no-results {
    color: #fff;
  }
`;

const LoadingContainer = styled.div`
  font-size: 1rem;
  line-height: 0;
  display: flex;
  align-items: center;
  height: 3.1875rem;
  text-transform: uppercase;
  font-size: 0.85rem;
  background-color: rgba(0, 0, 0, 0.35);
  color: rgba(255, 255, 255, 0.75);
  border: solid 1px #fff;
  padding-left: 0.5rem;
`;

const QuickLinks = styled.div`
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 1.5rem;
  justify-content: center;
`;

const QuickLink = styled.button`
  background-color: transparent;
  border: 1px solid ${secondaryColor};
  color: #fff;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-family: ${secondaryFont};
  font-size: 0.8rem;
  text-transform: uppercase;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${secondaryColor};
  }
`;

const Attribution = styled.div`
  position: fixed;
  bottom: 1rem;
  left: 0;
  right: 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.7rem;
  font-family: ${secondaryFont};

  a {
    color: rgba(255, 255, 255, 0.6);
    text-decoration: none;
    &:hover {
      color: #fff;
    }
  }
`;

const Landing = () => {
  const { loading, error, data } = useGlobalLocationData();
  const history = useHistory();
  const getString = useFluent();

  const navigateToRegion = useCallback(
    (regionId: string) => {
      const route = Routes.CityOverview.replace(":cityId", regionId);
      history.push(route);
    },
    [history],
  );

  const onSelect = useCallback(
    (val: ExtendedSearchDatum) => {
      if (val.level !== "0") {
        navigateToRegion(val.id as string);
      }
    },
    [navigateToRegion],
  );

  let searchBar: React.ReactElement<any>;
  if (loading === true) {
    searchBar = (
      <LoadingContainer>
        <SimpleLoader />
        {getString("global-ui-loading-cities")}...
      </LoadingContainer>
    );
  } else if (error !== undefined) {
    console.error(error);
    searchBar = (
      <LoadingContainer>
        <SimpleError color={"white"} />
      </LoadingContainer>
    );
  } else if (data !== undefined) {
    const searchData = locationDataToHierarchicalTreeData(data).map((d) => ({
      ...d,
      population: 0,
      gdp: 0,
    }));
    searchBar = (
      <SearchBar
        data={searchData}
        setHighlighted={onSelect}
        onPanelHover={() => {}}
        onTraverseLevel={() => {}}
        highlighted={null}
        focusOnRender={true}
      />
    );
  } else {
    searchBar = <></>;
  }

  return (
    <Root>
      <CenterPanel>
        <Heading />
        <SearchContainer>{searchBar}</SearchContainer>
        <QuickLinks>
          <QuickLink onClick={() => navigateToRegion("national-united-states")}>
            United States (National)
          </QuickLink>
          <QuickLink onClick={() => navigateToRegion("state-california")}>
            California
          </QuickLink>
          <QuickLink onClick={() => navigateToRegion("state-new-york")}>
            New York
          </QuickLink>
          <QuickLink onClick={() => navigateToRegion("state-texas")}>
            Texas
          </QuickLink>
        </QuickLinks>
      </CenterPanel>
      <Attribution>
        Based on{" "}
        <a
          href="https://metroverse.cid.harvard.edu/"
          target="_blank"
          rel="noopener noreferrer"
        >
          Metroverse
        </a>{" "}
        by Harvard Growth Lab. Licensed under CC BY-NC-SA 4.0.
        Data from{" "}
        <a
          href="https://www.bls.gov/oes/"
          target="_blank"
          rel="noopener noreferrer"
        >
          BLS OES
        </a>{" "}
        +{" "}
        <a
          href="https://www.onetonline.org/"
          target="_blank"
          rel="noopener noreferrer"
        >
          O*NET
        </a>
        .
      </Attribution>
    </Root>
  );
};

export default Landing;
