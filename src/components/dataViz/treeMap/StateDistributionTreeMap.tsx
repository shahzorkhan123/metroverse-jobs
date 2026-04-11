import React, { useRef, useEffect, useState } from "react";
import { useGlobalIndustryMap } from "../../../hooks/useGlobalIndustriesData";
import {
  ClassificationNaicsIndustry,
  CompositionType,
} from "../../../types/graphQL/graphQLTypes";
import { usePrevious } from "react-use";
import TreeMap, { transformData, Inputs } from "react-canvas-treemap";
import useSectorMap from "../../../hooks/useSectorMap";
import { useWindowWidth } from "../../../contextProviders/appContext";
import styled from "styled-components/macro";
import SimpleError from "../../transitionStateComponents/SimpleError";
import LoadingBlock, {
  LoadingOverlay,
} from "../../transitionStateComponents/VizLoadingBlock";
import ErrorBoundary from "../ErrorBoundary";
import useFluent from "../../../hooks/useFluent";
import { numberWithCommas } from "../../../Utils";
import { breakPoints } from "../../../styling/GlobalGrid";
import { Indicator } from "../../general/PreChartRow";
import SimpleTextLoading from "../../transitionStateComponents/SimpleTextLoading";
import { getStandardTooltip } from "../../../utilities/rapidTooltip";
import { rgba } from "polished";
import { formatNumber } from "../../../Utils";
import { useStaticData } from "../../../dataProvider";
import { getStateAbbreviation } from "../../../utils/stateAbbreviations";
import Tooltip from "../../general/Tooltip";

const Root = styled.div`
  width: 100%;
  height: 100%;
  grid-column: 1;
  grid-row: 2;
  position: relative;

  @media ${breakPoints.small} {
    grid-row: 3;
    grid-column: 1;
  }
`;

const TreeMapContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
`;

interface StateDistributionIndustry {
  id: string;
  stateId: string;
  stateName: string;
  majorGroupId: string;
  majorGroupName: string;
  numEmploy: number;
  numCompany: number;
  aMean: number;
}

interface SuccessResponse {
  industries: StateDistributionIndustry[];
}

/**
 * Fetch state distribution data: for each Level 1 occupation group,
 * show breakdown across all states.
 */
const useStateDistributionQuery = (variables: { year: number }) => {
  const { data: blsData, loading, error } = useStaticData();

  if (!blsData) {
    return { loading, error, data: undefined };
  }

  // Get all state regions
  const stateRegions = blsData.regions.filter(r => r.regionType === 'State');

  if (stateRegions.length === 0) {
    return { loading: false, error: undefined, data: { industries: [] } as SuccessResponse };
  }

  // Build Level 1 occupation groups from majorGroups
  const level1Groups = blsData.majorGroups.map(g => g.groupId);

  // Collect state × occupation cells
  const industries: StateDistributionIndustry[] = [];

  stateRegions.forEach(state => {
    const regionData = blsData.regionData[state.regionId];
    if (!regionData) return;

    const yearData = regionData[variables.year.toString()];
    if (!yearData) return;

    level1Groups.forEach(groupId => {
      // Find the Level 1 occupation record for this major group
      const occRecord = yearData.find(d => d.socCode === groupId || d.socCode === `${groupId}-0000`);
      if (!occRecord) return;

      const majorGroup = blsData.majorGroups.find(g => g.groupId === groupId);
      if (!majorGroup) return;

      industries.push({
        id: `${state.regionId}::${groupId}`,
        stateId: state.regionId,
        stateName: state.name,
        majorGroupId: groupId,
        majorGroupName: majorGroup.name,
        numEmploy: occRecord.totEmp || 0,
        numCompany: occRecord.gdp || 0,
        aMean: occRecord.aMean || 0,
      });
    });
  });

  return { loading: false, error: undefined, data: { industries } as SuccessResponse };
};

export { useStateDistributionQuery };

interface Props {
  year: number;
  compositionType: CompositionType;
  hiddenSectors: ClassificationNaicsIndustry["id"][];
  setIndicatorContent: (indicator: Indicator) => void;
}

const StateDistributionTreeMap = (props: Props) => {
  const {
    year,
    compositionType,
    hiddenSectors,
    setIndicatorContent,
  } = props;
  const industryMap = useGlobalIndustryMap();
  const getString = useFluent();
  const windowDimensions = useWindowWidth();
  const { countryMetadata } = useStaticData();
  const dynamicColorMap = useSectorMap();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const tooltipContentRef = useRef<HTMLDivElement | null>(null);
  const prevIndicatorKeyRef = useRef<string>('__init__');
  const [dimensions, setDimensions] = useState<
    { width: number; height: number } | undefined
  >(undefined);
  const { loading, error, data } = useStateDistributionQuery({ year });

  useEffect(() => {
    const node = rootRef.current;
    if (node) {
      setTimeout(() => {
        const { width, height } = node.getBoundingClientRect();
        setDimensions({ width, height });
      }, 0);
    }
  }, [rootRef, windowDimensions]);

  const prevData = usePrevious(data);
  let dataToUse: SuccessResponse | undefined;
  if (data) {
    dataToUse = data;
  } else if (prevData) {
    dataToUse = prevData;
  } else {
    dataToUse = undefined;
  }

  const indicator: Indicator = {
    text: undefined,
    tooltipContent: undefined,
  };
  let output: React.ReactElement<any> | null;

  if (industryMap.loading || !dimensions || (loading && prevData === undefined)) {
    indicator.text = (
      <>
        {getString("global-ui-sample-size") + ": "}
        <SimpleTextLoading />
      </>
    );
    output = <LoadingBlock />;
  } else if (error !== undefined) {
    indicator.text = getString("global-ui-sample-size") + ": ―";
    output = (
      <LoadingOverlay>
        <SimpleError />
      </LoadingOverlay>
    );
    console.error(error);
  } else if (industryMap.error !== undefined) {
    indicator.text = getString("global-ui-sample-size") + ": ―";
    output = (
      <LoadingOverlay>
        <SimpleError />
      </LoadingOverlay>
    );
    console.error(industryMap.error);
  } else if (dataToUse !== undefined) {
    const { industries } = dataToUse;

    const treeMapData: Inputs["data"] = [];
    let total = 0;

    industries.forEach(({ id, stateName, majorGroupId, numCompany, numEmploy }) => {
      if (hiddenSectors.includes(majorGroupId)) return;

      const companies = numCompany || 0;
      const employees = numEmploy || 0;

      total =
        compositionType === CompositionType.Companies
          ? total + companies
          : total + employees;
      const value =
        compositionType === CompositionType.Companies
          ? companies
          : employees;

      // Use state abbreviation as title for compact labels
      const stateAbbr = getStateAbbreviation(stateName, countryMetadata);

      treeMapData.push({
        id,
        value,
        title: stateAbbr,
        topLevelParentId: majorGroupId,
      });
    });

    if (!treeMapData.length) {
      indicator.text = getString("global-ui-sample-size") + ": ―";
      output = (
        <LoadingOverlay>
          <SimpleError
            fluentMessageId={"global-ui-error-no-sectors-selected"}
          />
        </LoadingOverlay>
      );
    } else {
      const transformed = transformData({
        data: treeMapData,
        width: dimensions.width,
        height: dimensions.height,
        colorMap: dynamicColorMap,
      });
      const loadingOverlay = loading ? <LoadingBlock /> : null;
      const onHover = (id: string) => {
        const node = tooltipContentRef.current;
        const industryWithData = industries.find((ind) => ind.id === id);
        if (industryWithData && node) {
          const color = dynamicColorMap.find(
            (c) => c.id === industryWithData.majorGroupId,
          );
          const numCompany = industryWithData.numCompany || 0;
          const numEmploy = industryWithData.numEmploy || 0;
          const aMean = industryWithData.aMean || 0;
          const value =
            compositionType === CompositionType.Employees
              ? numEmploy
              : numCompany;
          const share = (value / total) * 100;
          const shareString = share < 0.01 ? "<0.01%" : share.toFixed(2) + "%";
          const terminology = countryMetadata?.terminology;
          const wageLabel = terminology?.wage || "Avg Annual Wage";
          const empLabel = terminology?.employment || "Employees";
          const currSymbol = countryMetadata?.currencySymbol || "$";
          const rows: string[][] = [
            ["State:", industryWithData.stateName],
            ["Occupation:", industryWithData.majorGroupName],
            [getString("global-ui-year") + ":", year.toString()],
            [empLabel + ":", numberWithCommas(formatNumber(Math.round(numEmploy)))],
            [
              getString("tooltip-share-generic", { value: compositionType }) +
                ":",
              shareString,
            ],
            [wageLabel + ":", currSymbol + numberWithCommas(formatNumber(Math.round(aMean)))],
            ["Total Income:", currSymbol + numberWithCommas(formatNumber(Math.round(numCompany)))],
          ];
          node.innerHTML = getStandardTooltip({
            title: `${industryWithData.stateName} - ${industryWithData.majorGroupName}`,
            color: color ? rgba(color.color, 0.3) : "#fff",
            rows,
            boldColumns: [1, 2],
          });
        }
      };

      const fallbackTitle =
        "Treemap displaying state distribution across occupation groups. " +
        "Each cell represents a state within an occupation group.";
      output = (
        <TreeMapContainer>
          <Tooltip
            explanation={<div ref={tooltipContentRef} />}
            cursor={"default"}
            overrideStyles={true}
          >
            <ErrorBoundary>
              <TreeMap
                highlighted={undefined}
                cells={transformed.treeMapCells}
                numCellsTier={0}
                chartContainerWidth={dimensions.width}
                chartContainerHeight={dimensions.height}
                onCellClick={noop}
                onMouseOverCell={onHover}
                onMouseLeaveChart={noop}
                fallbackTitle={fallbackTitle}
              />
            </ErrorBoundary>
          </Tooltip>
          {loadingOverlay}
        </TreeMapContainer>
      );

      const totalNum = formatNumber(Math.round(total));
      indicator.text = getString("global-ui-sample-size") + ": " + numberWithCommas(totalNum);
    }
  } else {
    indicator.text = getString("global-ui-sample-size") + ": ―";
    output = null;
  }

  const indicatorKey = typeof indicator.text === 'string'
    ? indicator.text
    : indicator.text !== undefined ? '__loading__' : '__undefined__';
  if (indicatorKey !== prevIndicatorKeyRef.current) {
    prevIndicatorKeyRef.current = indicatorKey;
    setIndicatorContent(indicator);
  }

  return (
    <ErrorBoundary>
      <Root ref={rootRef}>
        {output}
      </Root>
    </ErrorBoundary>
  );
};

// Missing noop import
const noop = () => {};

export default StateDistributionTreeMap;
