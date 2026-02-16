import React, { useState, useRef } from "react";
import BasicModal from "../../../standardModal/BasicModal";
import styled from "styled-components/macro";
import {
  secondaryFont,
  primaryFont,
  SearchContainerDark,
  backgroundDark,
} from "../../../../styling/styleUtils";
import useFluent from "../../../../hooks/useFluent";
import PanelSearch, { Datum } from "react-panel-search";
import useCurrentCityId from "../../../../hooks/useCurrentCityId";
import useGlobalLocationData from "../../../../hooks/useGlobalLocationData";
import { useHistory } from "react-router-dom";
import queryString from "query-string";
import useQueryParams from "../../../../hooks/useQueryParams";
import { RegionGroup } from "../../../dataViz/comparisonBarChart/cityIndustryComparisonQuery";
import matchingKeywordFormatter from "../../../../styling/utils/panelSearchKeywordFormatter";
import { TooltipTheme } from "../../../general/Tooltip";
import BenchmarkSVG from "../../../../assets/icons/benchmark_comparator.svg";

// Stub: peer group counts not available in static data
export const usePeerGroupCityCount = (_cityId: string | null): {
  loading: boolean;
  error: any;
  data: { cityPeerGroupCounts: any } | undefined;
} => ({
  loading: false,
  error: undefined,
  data: undefined,
});

const mobileWidth = 750; // in px

const Root = styled.div`
  font-family: ${secondaryFont};
  color: #fff;
  width: 800px;
  max-width: 100%;
  height: 750px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  box-sizing: border-box;

  @media (max-width: 990px), (max-height: 800px) {
    width: 100%;
    height: auto;
    max-height: initial;
    padding: 1rem;
  }
`;

const benchmarkButtonClassName = "benchmark-open-modal-button-class-name";

const H1 = styled.h1`
  text-transform: uppercase;
  font-weight: 400;
  text-align: center;
  margin-top: 2rem;
  margin-bottom: 2rem;

  @media (max-width: 990px), (max-height: 800px) {
    font-size: 1.5rem;
    margin-top: 1rem;
    margin-bottom: 1rem;
  }
`;

const Icon = styled.img`
  width: 2.5rem;
  height: 2.5rem;
  position: relative;
  top: 0.75rem;
  margin-right: 1rem;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  grid-gap: 2rem;

  @media (max-width: ${mobileWidth}px) {
    grid-template-columns: auto;
    grid-template-rows: auto;
  }

  .react-panel-search-search-bar-input {
    background-color: ${backgroundDark};
  }

  .react-panel-search-highlighted-item {
    background-color: rgba(255, 255, 255, 0.25);
  }

  .react-panel-search-search-results {
    background-color: ${backgroundDark};
  }
`;

const ContinueButtonContainer = styled.div`
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  padding: 0 1rem 1rem;
  position: sticky;
  bottom: 0;
  pointer-events: none;

  @media (max-width: 750px) {
    position: relative;
    padding-top: 1rem;
  }

  @media (max-height: 800px) {
    margin-top: 0;
  }
`;

const ContinueButton = styled.button`
  background-color: transparent;
  border: solid 1px #fff;
  text-transform: uppercase;
  color: #fff;
  font-family: ${secondaryFont};
  font-size: 1.25rem;
  padding: 0.6rem 1rem;
  transition: opacity 0.2s ease-in-out;
  background-color: ${backgroundDark};
  pointer-events: all;

  &:hover:not(:disabled) {
    background-color: #fff;
    color: ${backgroundDark};
  }

  &:disabled {
    cursor: not-allowed;
    color: rgba(255, 255, 255, 0.5);
    border-color: rgba(255, 255, 255, 0.5);
  }

  @media (max-width: 990px), (max-height: 800px) {
    font-size: 1rem;
  }
`;

const ContainerTitle = styled.h3`
  color: #fff;
  font-weight: 400;
  margin: 0 0 0.4rem;
  font-family: ${primaryFont};

  @media (max-width: 990px), (max-height: 800px) {
    font-size: 1.1rem;
  }
`;

const AboutText = styled.p`
  color: #fff;
  padding: 0 1.5rem;
  margin: 0 0 1rem;
  font-family: ${primaryFont};

  @media (max-width: 990px), (max-height: 800px) {
    font-size: 0.8rem;
  }
`;

export const defaultBenchmark = RegionGroup.World;

export enum ComparisonType {
  Relative = "relative", // RCA
  Absolute = "absolute", // Econ composition
}

interface Props {
  closeModal: (value: string | undefined) => void;
  data: Datum[];
  comparisonType: ComparisonType;
}

const AddComparisonModal = (props: Props) => {
  const { closeModal, data, comparisonType } = props;
  const getString = useFluent();
  const cityId = useCurrentCityId();
  const continueButtonRef = useRef<HTMLButtonElement | null>(null);
  const { data: globalData } = useGlobalLocationData();
  const history = useHistory();
  const { benchmark, ...otherParams } = useQueryParams();
  let intialSelected: Datum | null | RegionGroup = RegionGroup.World;
  if (benchmark === RegionGroup.World) {
    intialSelected = benchmark as RegionGroup;
  }
  const [selected, setSelected] = useState<
    Datum | null | RegionGroup
  >(intialSelected);

  const currentCity = globalData
    ? globalData.cities.find((c) => c.cityId === cityId)
    : undefined;
  const name = currentCity ? currentCity.name : "";

  const selectCity = (city: Datum | null) => {
    setSelected(city);
    if (continueButtonRef && continueButtonRef.current) {
      const node = continueButtonRef.current;
      setTimeout(() => {
        node.focus();
      }, 0);
    }
  };

  const onContinue = () => {
    if (selected && typeof selected === "object") {
      const query = queryString.stringify({
        ...otherParams,
        benchmark: selected.id,
      });
      const newUrl = query
        ? history.location.pathname + "?" + query
        : history.location.pathname;
      history.push(newUrl);
      closeModal(selected.id.toString());
    } else if (typeof selected === "string") {
      const query = queryString.stringify({
        ...otherParams,
        benchmark: selected,
      });
      const newUrl = query
        ? history.location.pathname + "?" + query
        : history.location.pathname;
      history.push(newUrl);
      closeModal(RegionGroup.World);
    }
  };

  const prevValue = benchmark;
  const closeModalWithoutConfirming =
    prevValue === undefined
      ? () => closeModal(RegionGroup.World as string)
      : () => closeModal(prevValue);

  const title =
    comparisonType === ComparisonType.Relative
      ? getString("global-ui-benchmark-title")
      : getString("global-ui-compare-title", { name });

  const selectCityTitle =
    comparisonType === ComparisonType.Relative
      ? getString("global-ui-select-benchmark-city")
      : getString("global-ui-select-a-city-name");

  const about =
    comparisonType === ComparisonType.Relative ? (
      <AboutText>
        Select a region to compare against.
      </AboutText>
    ) : null;

  return (
    <BasicModal
      onClose={closeModalWithoutConfirming}
      width={"auto"}
      height={"inherit"}
    >
      <Root>
        <H1
          style={
            comparisonType === ComparisonType.Absolute
              ? { marginBottom: "4rem" }
              : undefined
          }
          className={
            comparisonType === ComparisonType.Absolute
              ? undefined
              : benchmarkButtonClassName
          }
        >
          <Icon src={BenchmarkSVG} />
          {title}:
        </H1>
        {about}
        <SearchContainerDark>
          <Grid>
            <div>
              <ContainerTitle>{selectCityTitle}</ContainerTitle>
              <PanelSearch
                data={data.filter(({ id }) => id !== cityId)}
                topLevelTitle={getString("global-text-countries")}
                disallowSelectionLevels={["0"]}
                defaultPlaceholderText={getString("global-ui-type-a-city-name")}
                showCount={true}
                resultsIdentation={1.75}
                neverEmpty={false}
                maxResults={500}
                selectedValue={typeof selected === "object" ? selected : null}
                onSelect={selectCity}
                focusOnRender={
                  window.innerHeight > 800 && window.innerWidth > 990
                }
                matchingKeywordFormatter={matchingKeywordFormatter(
                  TooltipTheme.Dark,
                )}
              />
            </div>
          </Grid>
        </SearchContainerDark>
        <ContinueButtonContainer>
          <ContinueButton
            onClick={onContinue}
            ref={continueButtonRef}
            disabled={!selected}
          >
            {getString("global-ui-continue")}
          </ContinueButton>
        </ContinueButtonContainer>
      </Root>
    </BasicModal>
  );
};

export default AddComparisonModal;
