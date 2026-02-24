import orderBy from "lodash/orderBy";
import React from "react";
import Tooltip from "../../../../../../components/general/Tooltip";
import useCurrentCityId from "../../../../../../hooks/useCurrentCityId";
import useFluent from "../../../../../../hooks/useFluent";
import { defaultYear } from "../../../../../../Utils";
import { Icon, ListItem, TitleBase, ValueBase, YearText } from "../styleUtils";
import TopCitiesSVG from "../../../../../../assets/icons/topsimilarcities.svg";
import SimpleTextLoading from "../../../../../../components/transitionStateComponents/SimpleTextLoading";
import { useStaticData } from "../../../../../../dataProvider";

const TopCities = () => {
  const getString = useFluent();
  const cityId = useCurrentCityId();
  const { data: blsData, loading, selectedYear } = useStaticData();
  let topCitiesElement: React.ReactElement<any> | null;
  if (loading || !blsData || !cityId) {
    topCitiesElement = <SimpleTextLoading />;
  } else {
    const yearDataByRegion = blsData.regionData[cityId] || {};
    const records =
      yearDataByRegion[selectedYear] ||
      yearDataByRegion[Object.keys(yearDataByRegion)[0]] ||
      [];
    const occMap = new Map(blsData.occupations.map((o) => [o.socCode, o]));

    const topWageOccupations = orderBy(
      records.filter((r) => (r.aMean || 0) > 0),
      ["aMean"],
      ["desc"],
    )
      .slice(0, 3)
      .map((r) => {
        const occName = occMap.get(r.socCode)?.name || r.socCode;
        return (
          <ListItem key={r.socCode}>
            {occName.toUpperCase()}
          </ListItem>
        );
      });

    topCitiesElement = <>{topWageOccupations}</>;
  }
  return (
    <div>
      <TitleBase>
        <Icon src={TopCitiesSVG} />
        <div>Highest Wage Occupations</div>
        <YearText>
          {selectedYear || defaultYear}
          <Tooltip
            explanation={getString("city-overview-top-specialized-industries-tooltip")}
          />
        </YearText>
      </TitleBase>
      <ValueBase>{topCitiesElement}</ValueBase>
    </div>
  );
};

export default TopCities;
