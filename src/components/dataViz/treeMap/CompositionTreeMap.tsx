import React, { useRef, useEffect, useState, useCallback } from "react";
import { useGlobalIndustryMap } from "../../../hooks/useGlobalIndustriesData";
import {
  DigitLevel,
  ClassificationNaicsIndustry,
  CompositionType,
} from "../../../types/graphQL/graphQLTypes";
import { usePrevious } from "react-use";
import TreeMap, { transformData, Inputs } from "react-canvas-treemap";
import {
  sectorColorMap,
  educationColorRange,
  wageColorRange,
} from "../../../styling/styleUtils";
import { useWindowWidth } from "../../../contextProviders/appContext";
import styled from "styled-components/macro";
import noop from "lodash/noop";
import SimpleError from "../../transitionStateComponents/SimpleError";
import LoadingBlock, {
  LoadingOverlay,
} from "../../transitionStateComponents/VizLoadingBlock";
import Tooltip from "../../general/Tooltip";
import ErrorBoundary from "../ErrorBoundary";
import useFluent from "../../../hooks/useFluent";
import { numberWithCommas } from "../../../Utils";
import { breakPoints } from "../../../styling/GlobalGrid";
import { Indicator } from "../../general/PreChartRow";
import SimpleTextLoading from "../../transitionStateComponents/SimpleTextLoading";
import {
  RapidTooltipRoot,
  getStandardTooltip,
} from "../../../utilities/rapidTooltip";
import { rgba } from "polished";
import { ColorBy } from "../../../routing/routes";
import { useAggregateIndustryMap } from "../../../hooks/useAggregateIndustriesData";
import { defaultYear, formatNumber } from "../../../Utils";
import { scaleLinear } from "d3-scale";
import QuickError from "../../transitionStateComponents/QuickError";
import { useStaticData } from "../../../dataProvider";

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

/** Get parent SOC code for hierarchy traversal.
 *  For level 3 (XX-XXX0), the minor-group parent can be XX-X000 (standard)
 *  or XX-XX00 (SOC 2018 renumbered).  When knownCodes is provided we pick
 *  whichever pattern actually exists; otherwise default to XX-X000.
 */
function socParent(code: string, knownCodes?: Set<string>): string | null {
  const prefix = code.substring(0, 3); // "XX-"
  const digits = code.substring(3);    // "YYYY"
  if (code.endsWith("-0000")) return null;  // level 1
  if (code.endsWith("00")) return prefix + "0000";  // level 2 → level 1
  if (code.endsWith("0")) {
    // level 3 → level 2: resolve ambiguous minor-group parent
    const renumbered = prefix + digits.substring(0, 2) + "00";
    const standard   = prefix + digits[0] + "000";
    if (renumbered === standard) return standard;
    if (knownCodes) {
      return knownCodes.has(renumbered) ? renumbered : standard;
    }
    return standard;
  }
  return prefix + digits.substring(0, 3) + "0";  // level 4 → level 3
}

interface EconomicCompositionIndustry {
  id: string;
  naicsId: string;
  numCompany: number | null;
  numEmploy: number | null;
  aMean: number | null;
}

interface SuccessResponse {
  industries: EconomicCompositionIndustry[];
}

/**
 * Static data replacement for the ECONOMIC_COMPOSITION_QUERY.
 * Reads from StaticDataProvider instead of GraphQL.
 */
const useEconomicCompositionQuery = (variables: { cityId: string; year: number }) => {
  const { data: blsData, loading, error } = useStaticData();

  if (!blsData) {
    return { loading, error, data: undefined };
  }

  const regionData = blsData.regionData[variables.cityId];
  if (!regionData) {
    return { loading: false, error: undefined, data: { industries: [] } as SuccessResponse };
  }

  const yearData = regionData[variables.year.toString()];
  if (!yearData) {
    return { loading: false, error: undefined, data: { industries: [] } as SuccessResponse };
  }

  const industries: EconomicCompositionIndustry[] = yearData.map((d) => ({
    id: d.socCode,
    naicsId: d.socCode,
    numCompany: d.gdp,      // GDP maps to "companies/establishments"
    numEmploy: d.totEmp,     // Employment maps directly
    aMean: d.aMean,          // Average annual wage
  }));

  return { loading: false, error: undefined, data: { industries } as SuccessResponse };
};

export { useEconomicCompositionQuery };

interface Props {
  cityId: string;
  year: number;
  highlighted: string | undefined;
  clearHighlighted: () => void;
  digitLevel: DigitLevel;
  colorBy: ColorBy;
  compositionType: CompositionType;
  hiddenSectors: ClassificationNaicsIndustry["id"][];
  setIndicatorContent: (indicator: Indicator) => void;
  onDrillDown?: (sectorId: string, currentLevel: number) => void;
}

const CompositionTreeMap = (props: Props) => {
  const {
    cityId,
    year,
    digitLevel,
    compositionType,
    highlighted,
    hiddenSectors,
    colorBy,
    setIndicatorContent,
  } = props;
  const industryMap = useGlobalIndustryMap();
  const getString = useFluent();
  const windowDimensions = useWindowWidth();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const tooltipContentRef = useRef<HTMLDivElement | null>(null);
  const highlightedTooltipRef = useRef<HTMLDivElement | null>(null);
  const [dimensions, setDimensions] = useState<
    { width: number; height: number } | undefined
  >(undefined);
  const { loading, error, data } = useEconomicCompositionQuery({
    cityId,
    year,
  });
  const aggregateIndustryDataMap = useAggregateIndustryMap({
    level: digitLevel,
    year: defaultYear,
  });

  const onCellClick = useCallback((id: string) => {
    if (!props.onDrillDown) return;
    const industry = industryMap.data[id];
    if (!industry) return;
    const sectorId = industry.naicsIdTopParent.toString();
    props.onDrillDown(sectorId, digitLevel);
  }, [industryMap, digitLevel, props]);

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
  if (
    industryMap.loading ||
    !dimensions ||
    (loading && prevData === undefined) ||
    ((colorBy === ColorBy.education || colorBy === ColorBy.wage) &&
      aggregateIndustryDataMap.loading)
  ) {
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
  } else if (
    aggregateIndustryDataMap.error !== undefined &&
    (colorBy === ColorBy.education || colorBy === ColorBy.wage)
  ) {
    indicator.text = getString("global-ui-sample-size") + ": ―";
    output = (
      <LoadingOverlay>
        <SimpleError />
      </LoadingOverlay>
    );
    console.error(aggregateIndustryDataMap.error);
  } else if (dataToUse !== undefined) {
    const { industries } = dataToUse;

    // Smart hierarchical filter: show finest available level per SOC branch,
    // falling back to parents when children are missing (BLS data suppression).
    // Walk up the hierarchy to find the nearest available ancestor (handles
    // gaps like missing level 2 data in state files).
    const availableCodes = new Set(industries.map((i) => i.naicsId));
    const childrenOf = new Map<string, string[]>();
    for (const { naicsId } of industries) {
      const ind = industryMap.data[naicsId];
      if (ind && ind.level !== null && ind.level <= digitLevel) {
        let ancestor = socParent(naicsId, availableCodes);
        while (ancestor && !availableCodes.has(ancestor)) {
          ancestor = socParent(ancestor, availableCodes);
        }
        if (ancestor) {
          if (!childrenOf.has(ancestor)) childrenOf.set(ancestor, []);
          childrenOf.get(ancestor)!.push(naicsId);
        }
      }
    }

    // Pre-compute residual values for parents with partial child coverage.
    // BLS doesn't publish all intermediate SOC levels for states/metros,
    // so a parent may have only some branches covered by children.
    // Show the parent as a residual (parent_total - children_sum) to
    // avoid both double-counting and losing uncovered branches.
    const residualValues = new Map<string, { employ: number; company: number }>();
    childrenOf.forEach((children, parentCode) => {
      const parentInd = industries.find((i) => i.naicsId === parentCode);
      if (!parentInd) return;
      const parentEmploy = parentInd.numEmploy || 0;
      const parentCompany = parentInd.numCompany || 0;
      let childEmploySum = 0;
      let childCompanySum = 0;
      children.forEach((childCode) => {
        const childInd = industries.find((i) => i.naicsId === childCode);
        if (childInd) {
          childEmploySum += childInd.numEmploy || 0;
          childCompanySum += childInd.numCompany || 0;
        }
      });
      residualValues.set(parentCode, {
        employ: Math.max(0, parentEmploy - childEmploySum),
        company: Math.max(0, parentCompany - childCompanySum),
      });
    });

    const treeMapData: Inputs["data"] = [];
    // Track adjusted values for tooltip consistency (residual for parents, full for leaves)
    const adjustedValueMap = new Map<string, { employ: number; company: number }>();
    let total = 0;
    industries.forEach(({ naicsId, numCompany, numEmploy }) => {
      const industry = industryMap.data[naicsId];
      if (industry && industry.level !== null && industry.level <= digitLevel) {
        const { name, naicsIdTopParent } = industry;
        if (hiddenSectors.includes(naicsIdTopParent.toString())) return;

        const children = childrenOf.get(naicsId) || [];
        const hasVisibleChildren = children.some((c) => {
          const ci = industryMap.data[c];
          return ci && ci.level !== null && ci.level <= digitLevel && availableCodes.has(c);
        });

        let companies = numCompany ? numCompany : 0;
        let employees = numEmploy ? numEmploy : 0;

        if (hasVisibleChildren) {
          // Parent with children: use residual (uncovered portion)
          const residual = residualValues.get(naicsId);
          if (!residual || (residual.employ <= 0 && residual.company <= 0)) {
            return; // Fully covered by children, skip
          }
          companies = residual.company;
          employees = residual.employ;
        }

        adjustedValueMap.set(naicsId, { employ: employees, company: companies });
        total =
          compositionType === CompositionType.Companies
            ? total + companies
            : total + employees;
        const value =
          compositionType === CompositionType.Companies
            ? companies
            : employees;
        treeMapData.push({
          id: naicsId,
          value,
          title: name ? name : "",
          topLevelParentId: naicsIdTopParent.toString(),
        });
      }
    });
    let colorScale: (val: number) => string | undefined;
    if (
      colorBy === ColorBy.education &&
      aggregateIndustryDataMap.data !== undefined
    ) {
      colorScale = scaleLinear()
        .domain([
          aggregateIndustryDataMap.data.globalMinMax.minYearsEducation,
          aggregateIndustryDataMap.data.globalMinMax.medianYearsEducation,
          aggregateIndustryDataMap.data.globalMinMax.maxYearsEducation,
        ])
        .range(educationColorRange as any) as any;
    } else if (
      colorBy === ColorBy.wage &&
      aggregateIndustryDataMap.data !== undefined
    ) {
      colorScale = scaleLinear()
        .domain([
          aggregateIndustryDataMap.data.globalMinMax.minHourlyWage,
          aggregateIndustryDataMap.data.globalMinMax.medianHourlyWage,
          aggregateIndustryDataMap.data.globalMinMax.maxHourlyWage,
        ])
        .range(wageColorRange as any) as any;
    } else {
      colorScale = () => undefined;
    }
    for (const i in treeMapData) {
      if (treeMapData[i] !== undefined) {
        let fill: string | undefined;
        if (
          (colorBy === ColorBy.education || colorBy === ColorBy.wage) &&
          aggregateIndustryDataMap.data
        ) {
          const target =
            aggregateIndustryDataMap.data.industries[treeMapData[i].id];
          if (target) {
            const targetValue =
              colorBy === ColorBy.education
                ? target.yearsEducationRank
                : target.hourlyWageRank;
            fill = colorScale(targetValue);
          }
        }
        treeMapData[i].fill = fill;
      }
    }
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
        colorMap: sectorColorMap,
      });
      const loadingOverlay = loading ? <LoadingBlock /> : null;
      const onHover = (id: string) => {
        const node = tooltipContentRef.current;
        const industry = industryMap.data[id];
        const industryWithData = industries.find(
          ({ naicsId }) => naicsId === id,
        );
        if (industry && industryWithData && node) {
          const color = sectorColorMap.find(
            (c) => c.id === industry.naicsIdTopParent.toString(),
          );
          // Use adjusted values (residual for parents) for consistent display
          const adjusted = adjustedValueMap.get(id);
          const numCompany = adjusted
            ? adjusted.company
            : industryWithData.numCompany || 0;
          const numEmploy = adjusted
            ? adjusted.employ
            : industryWithData.numEmploy || 0;
          const aMean = industryWithData.aMean ? industryWithData.aMean : 0;
          const value =
            compositionType === CompositionType.Employees
              ? numEmploy
              : numCompany;
          const share = (value / total) * 100;
          const shareString = share < 0.01 ? "<0.01%" : share.toFixed(2) + "%";
          const rows: string[][] = [
            [getString("global-ui-naics-code") + ":", industry.code],
            [getString("global-ui-year") + ":", year.toString()],
            ["Employees:", numberWithCommas(formatNumber(Math.round(numEmploy)))],
            [
              getString("tooltip-share-generic", { value: compositionType }) +
                ":",
              shareString,
            ],
            ["Avg Annual Wage:", "$" + numberWithCommas(formatNumber(Math.round(aMean)))],
            ["Total Income:", "$" + numberWithCommas(formatNumber(Math.round(numCompany)))],
          ];
          if (
            (colorBy === ColorBy.education || colorBy === ColorBy.wage) &&
            aggregateIndustryDataMap.data
          ) {
            const target =
              aggregateIndustryDataMap.data.industries[industry.naicsId];
            if (target) {
              const targetValue =
                colorBy === ColorBy.education
                  ? target.yearsEducation
                  : target.hourlyWage;
              rows.push([
                getString("global-formatted-color-by", { type: colorBy }),
                (colorBy === ColorBy.wage ? "$" : "") + targetValue.toFixed(2),
              ]);
            }
          }
          node.innerHTML = getStandardTooltip({
            title: industry.name ? industry.name : "",
            color: color ? rgba(color.color, 0.3) : "#fff",
            rows,
            boldColumns: [1, 2],
          });
        }
      };

      const highlightedCell = transformed.treeMapCells.find(
        (d) => d.id === highlighted,
      );

      if (highlighted && highlightedCell) {
        const node = highlightedTooltipRef.current;
        const industry = industryMap.data[highlighted];
        const industryWithData = industries.find(
          ({ naicsId }) => naicsId === highlighted,
        );
        if (industry && industryWithData && node) {
          const color = sectorColorMap.find(
            (c) => c.id === industry.naicsIdTopParent.toString(),
          );
          // Use adjusted values (residual for parents) for consistent display
          const hAdj = adjustedValueMap.get(highlighted);
          const numCompany = hAdj
            ? hAdj.company
            : industryWithData.numCompany || 0;
          const numEmploy = hAdj
            ? hAdj.employ
            : industryWithData.numEmploy || 0;
          const aMean = industryWithData.aMean ? industryWithData.aMean : 0;
          const value =
            compositionType === CompositionType.Employees
              ? numEmploy
              : numCompany;
          const share = (value / total) * 100;
          const shareString = share < 0.01 ? "<0.01%" : share.toFixed(2) + "%";
          const rows: string[][] = [
            [getString("global-ui-naics-code") + ":", industry.code],
            [getString("global-ui-year") + ":", year.toString()],
            ["Employees:", numberWithCommas(formatNumber(Math.round(numEmploy)))],
            [
              getString("tooltip-share-generic", { value: compositionType }) +
                ":",
              shareString,
            ],
            ["Avg Annual Wage:", "$" + numberWithCommas(formatNumber(Math.round(aMean)))],
            ["Total Income:", "$" + numberWithCommas(formatNumber(Math.round(numCompany)))],
          ];
          if (
            (colorBy === ColorBy.education || colorBy === ColorBy.wage) &&
            aggregateIndustryDataMap.data
          ) {
            const target =
              aggregateIndustryDataMap.data.industries[industry.naicsId];
            if (target) {
              const targetValue =
                colorBy === ColorBy.education
                  ? target.yearsEducation
                  : target.hourlyWage;
              rows.push([
                getString("global-formatted-color-by", { type: colorBy }),
                (colorBy === ColorBy.wage ? "$" : "") + targetValue.toFixed(2),
              ]);
            }
          }
          node.innerHTML =
            getStandardTooltip({
              title: industry.name ? industry.name : "",
              color: color ? rgba(color.color, 0.3) : "#fff",
              rows,
              boldColumns: [1, 2],
            }) +
            `
           <div style="position:absolute;top: -5px;right:2px;font-size:1.1rem;">×</div>
          `;
          node.style.position = "absolute";
          node.style.pointerEvents = "all";
          node.style.cursor = "pointer";
          node.style.display = "block";
          node.style.left =
            highlightedCell.x0 +
            (highlightedCell.x1 - highlightedCell.x0) / 2 +
            "px";
          node.style.top = highlightedCell.y0 + 16 + "px";
          const clearHighlighted = () => {
            props.clearHighlighted();
            node.removeEventListener("click", clearHighlighted);
          };
          node.addEventListener("click", clearHighlighted);
        }
      } else {
        const node = highlightedTooltipRef.current;
        if (node) {
          node.style.display = "none";
        }
      }

      const highlightErrorPopup =
        highlighted && !highlightedCell ? (
          <QuickError closeError={props.clearHighlighted}>
            {getString("global-ui-error-industry-not-in-data-set")}
          </QuickError>
        ) : null;

      indicator.text = loading ? (
        <>
          {getString("global-ui-sample-size") + ": "}
          <SimpleTextLoading />
        </>
      ) : (
        `${getString("global-ui-sample-size")}: ${numberWithCommas(formatNumber(Math.round(total)))} ` +
        getString("global-ui-estimated-total-employees")
      );
      indicator.tooltipContent = getString("glossary-total-shown");
      const fallbackTitle =
        "Treemap displaying the economic composition of the selected region " +
        "based on the number of " +
        compositionType +
        " found within the region. " +
        "The top values are as follows: ";
      output = (
        <TreeMapContainer>
          <Tooltip
            explanation={<div ref={tooltipContentRef} />}
            cursor={"default"}
            overrideStyles={true}
          >
            <ErrorBoundary>
              <TreeMap
                highlighted={highlighted}
                cells={transformed.treeMapCells}
                numCellsTier={0}
                chartContainerWidth={dimensions.width}
                chartContainerHeight={dimensions.height}
                onCellClick={onCellClick}
                onMouseOverCell={onHover}
                onMouseLeaveChart={noop}
                fallbackTitle={fallbackTitle}
              />
            </ErrorBoundary>
          </Tooltip>
          {loadingOverlay}
          {highlightErrorPopup}
        </TreeMapContainer>
      );
    }
  } else {
    output = null;
  }

  setIndicatorContent(indicator);
  return (
    <>
      <Root ref={rootRef}>
        {output}
        <RapidTooltipRoot ref={highlightedTooltipRef} />
      </Root>
    </>
  );
};

export default React.memo(CompositionTreeMap);
