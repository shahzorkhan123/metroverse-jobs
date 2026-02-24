import React from "react";
import useCurrentCityId from "../../../../../../hooks/useCurrentCityId";
import { TitleBase, YearText, Icon, ValueBase, ListItem } from "../styleUtils";
import PopulationSVG from "../../../../../../assets/icons/population.svg";
import RankingSVG from "../../../../../../assets/icons/ranking.svg";
import GdpPerCapitaSVG from "../../../../../../assets/icons/gdppercapita.svg";
import DataReliabilitySVG from "../../../../../../assets/icons/datareliability.svg";
import {
  defaultYear,
  formatNumberLong,
  numberWithCommas,
} from "../../../../../../Utils";
import useTerminology from "../../../../../../hooks/useTerminology";
import { useStaticData } from "../../../../../../dataProvider";

import styled from "styled-components";
import Tooltip from "../../../../../../components/general/Tooltip";
import SimpleTextLoading from "../../../../../../components/transitionStateComponents/SimpleTextLoading";
import {
  NewDataQualityLevel,
  dataQualityColors,
} from "../../../../../../components/general/Utils";

const DataLegend = styled.div`
  margin-right: 0.2rem;
  display: inline-flex;
  flex-direction: row;
  align-items: center;
`;

const SmallDot = styled.div`
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 1000px;
  margin-right: 0.2rem;
`;

const LargeDot = styled.div`
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 1000px;
  margin-right: 0.075rem;
`;

const LegendContainer = styled.div`
  margin-top: 0.5rem;

  & h1 {
    font-size: inherit;
  }
`;

const LegendRow = styled.div`
  margin-top: 0.25rem;
  font-size: 0.85em;
  display: flex;
  flex-direction: row;
  align-items: center;
`;

const TopRow = () => {
  const cityId = useCurrentCityId();
  const { data: blsData, loading, selectedYear } = useStaticData();
  const terminology = useTerminology();

  let workersElement: React.ReactElement<any> | null;
  let wageElement: React.ReactElement<any> | null;
  let incomeElement: React.ReactElement<any> | null;
  let coverageElement: React.ReactElement<any> | null;
  let flagColor: React.ReactElement<any> | null = null;
  let qualityLabel = "---";
  let dataQualityTooltip: React.ReactElement<any> | string = "---";

  if (loading || !blsData || !cityId) {
    workersElement = <SimpleTextLoading />;
    wageElement = <SimpleTextLoading />;
    incomeElement = <SimpleTextLoading />;
    coverageElement = <SimpleTextLoading />;
  } else {
    const yearDataByRegion = blsData.regionData[cityId] || {};
    const records =
      yearDataByRegion[selectedYear] ||
      yearDataByRegion[defaultYear] ||
      Object.values(yearDataByRegion)[0] ||
      [];

    if (records.length === 0) {
      workersElement = <>---</>;
      wageElement = <>---</>;
      incomeElement = <>---</>;
      coverageElement = <>---</>;
    } else {
      const occLevelByCode = new Map<string, number>();
      blsData.occupations.forEach((o) => occLevelByCode.set(o.socCode, o.level));

      const levels = records
        .map((r) => occLevelByCode.get(r.socCode))
        .filter((lvl): lvl is number => lvl !== undefined);

      const minLevel = levels.length > 0 ? Math.min(...levels) : 1;
      const maxLevel = levels.length > 0 ? Math.max(...levels) : 1;
      const baseLevelRecords = records.filter(
        (r) => (occLevelByCode.get(r.socCode) || minLevel) === minLevel,
      );

      const totalWorkers = baseLevelRecords.reduce(
        (sum, r) => sum + (r.totEmp || 0),
        0,
      );
      const totalIncome = baseLevelRecords.reduce((sum, r) => sum + (r.gdp || 0), 0);
      const avgWage = totalWorkers > 0 ? Math.round(totalIncome / totalWorkers) : 0;
      const wageCoverage =
        baseLevelRecords.filter((r) => (r.aMean || 0) > 0).length /
        Math.max(baseLevelRecords.length, 1);

      let dataQualityLevel = NewDataQualityLevel.LOW;
      if (wageCoverage >= 0.9) {
        dataQualityLevel = NewDataQualityLevel.HIGH;
      } else if (wageCoverage >= 0.75) {
        dataQualityLevel = NewDataQualityLevel.MEDIUM;
      }

      qualityLabel =
        dataQualityLevel === NewDataQualityLevel.HIGH
          ? "High"
          : dataQualityLevel === NewDataQualityLevel.MEDIUM
            ? "Medium"
            : "Low";

      dataQualityTooltip = (
        <>
          <div>
            Based on share of occupations with positive wage values in this region.
          </div>
          <LegendContainer>
            <h1>Data Quality Scale</h1>
            <LegendRow>
              <SmallDot
                style={{
                  backgroundColor: dataQualityColors.get(NewDataQualityLevel.HIGH),
                }}
              />
              High (≥90% wage coverage)
            </LegendRow>
            <LegendRow>
              <SmallDot
                style={{
                  backgroundColor: dataQualityColors.get(NewDataQualityLevel.MEDIUM),
                }}
              />
              Medium (75–89%)
            </LegendRow>
            <LegendRow>
              <SmallDot
                style={{
                  backgroundColor: dataQualityColors.get(NewDataQualityLevel.LOW),
                }}
              />
              Low (&lt;75%)
            </LegendRow>
          </LegendContainer>
        </>
      );

      flagColor = (
        <DataLegend>
          <LargeDot
            style={{ backgroundColor: dataQualityColors.get(dataQualityLevel) }}
          />
        </DataLegend>
      );

      workersElement = <>{formatNumberLong(totalWorkers)}</>;
      wageElement = <>${numberWithCommas(avgWage)}</>;
      incomeElement = <>{formatNumberLong(totalIncome)}</>;
      coverageElement = (
        <>
          <ListItem>{records.length} occupations</ListItem>
          <ListItem>
            Levels {minLevel}-{maxLevel}
          </ListItem>
        </>
      );
    }
  }

  return (
    <>
      <div>
        <TitleBase>
          <Icon src={PopulationSVG} />
          {terminology.employment}
          <YearText>
            {selectedYear}
            <Tooltip explanation={`Total ${terminology.employment.toLowerCase()} at base occupation level`} />
          </YearText>
        </TitleBase>
        <ValueBase>{workersElement}</ValueBase>
      </div>
      <div>
        <TitleBase>
          <Icon src={GdpPerCapitaSVG} />
          {terminology.wage}
          <YearText>
            {selectedYear}
            <Tooltip explanation={`Weighted average ${terminology.wage.toLowerCase()} in selected region`} />
          </YearText>
        </TitleBase>
        <ValueBase>{wageElement}</ValueBase>
      </div>
      <div>
        <TitleBase>
          <Icon src={RankingSVG} />
          Estimated Income
          <YearText>{selectedYear}</YearText>
        </TitleBase>
        <ValueBase>{incomeElement}</ValueBase>
      </div>
      <div>
        <TitleBase>
          <Icon src={DataReliabilitySVG} />
          Data Coverage
          <YearText>
            {selectedYear}
            <Tooltip explanation={dataQualityTooltip} />
          </YearText>
        </TitleBase>
        <ValueBase>
          {flagColor}
          {qualityLabel}
          {coverageElement}
        </ValueBase>
      </div>
    </>
  );
};

export default TopRow;
