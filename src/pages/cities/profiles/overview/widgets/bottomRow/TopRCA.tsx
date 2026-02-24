import React from "react";
import orderBy from "lodash/orderBy";
import useFluent from "../../../../../../hooks/useFluent";
import { useStaticData } from "../../../../../../dataProvider";
import {
  Icon,
  ListItem,
  TitleBase,
  ValueBase,
  WrappableText,
  YearText,
} from "../styleUtils";
import Tooltip from "../../../../../../components/general/Tooltip";
import TopIndustriesSVG from "../../../../../../assets/icons/topindustries.svg";
import SimpleTextLoading from "../../../../../../components/transitionStateComponents/SimpleTextLoading";
import styled from "styled-components";
import { breakPoints } from "../../../../../../styling/GlobalGrid";

const Cell = styled.div`
  max-width: 380px;
  @media ${breakPoints.small} {
    max-width: 100%;
  }
`;

interface Props {
  cityId: string;
}

const TopRCA = ({ cityId }: Props) => {
  const getString = useFluent();
  const { data: blsData, loading, selectedYear } = useStaticData();

  let topIndustriesElement: React.ReactElement<any> | null;
  if (loading || !blsData) {
    topIndustriesElement = <SimpleTextLoading />;
  } else {
    const yearDataByRegion = blsData.regionData[cityId] || {};
    const records =
      yearDataByRegion[selectedYear] ||
      yearDataByRegion[Object.keys(yearDataByRegion)[0]] ||
      [];
    const occMap = new Map(blsData.occupations.map((o) => [o.socCode, o]));

    const minLevel = records.reduce((min, r) => {
      const level = occMap.get(r.socCode)?.level || min;
      return Math.min(min, level);
    }, Number.MAX_SAFE_INTEGER);

    const topIndustries = orderBy(
      records.filter((r) => (occMap.get(r.socCode)?.level || minLevel) === minLevel),
      ["totEmp"],
      ["desc"],
    )
      .slice(0, 3)
      .map((r) => {
        const occName = occMap.get(r.socCode)?.name || r.socCode;
        return <ListItem key={r.socCode}>{occName.toUpperCase()}</ListItem>;
      });

    topIndustriesElement = <>{topIndustries}</>;
  }

  return (
    <>
      <Cell>
        <TitleBase>
          <Icon src={TopIndustriesSVG} />
          <WrappableText>
            {getString("city-overview-top-specialized-industries")}
          </WrappableText>
          <YearText>
            {selectedYear}
            <Tooltip
              explanation={getString("city-overview-top-specialized-industries-tooltip")}
            />
          </YearText>
        </TitleBase>
        <ValueBase>{topIndustriesElement}</ValueBase>
      </Cell>
    </>
  );
};

export default TopRCA;
