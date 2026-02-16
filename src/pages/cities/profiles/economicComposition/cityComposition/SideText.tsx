import React from "react";
import StandardSideTextBlock from "../../../../../components/general/StandardSideTextBlock";
import {
  ContentParagraph,
  ContentTitle,
} from "../../../../../styling/styleUtils";
import useFluent, {
  possessive,
  ordinalNumber,
} from "../../../../../hooks/useFluent";
import useCurrentCity from "../../../../../hooks/useCurrentCity";
import useGlobalLocationData from "../../../../../hooks/useGlobalLocationData";
import StandardSideTextLoading from "../../../../../components/transitionStateComponents/StandardSideTextLoading";
import { formatNumberLong } from "../../../../../Utils";
import { useEconomicCompositionQuery } from "../../../../../components/dataViz/treeMap/CompositionTreeMap";
import { useGlobalIndustryMap } from "../../../../../hooks/useGlobalIndustriesData";
import {
  DigitLevel,
  CompositionType,
} from "../../../../../types/graphQL/graphQLTypes";
import orderBy from "lodash/orderBy";
import Helmet from "react-helmet";

interface Props {
  year: number;
  cityId: string;
  compositionType: CompositionType;
}

interface IndustryDatum {
  name: string;
  sector: string;
  count: number;
}

const SideText = ({ year, cityId, compositionType }: Props) => {
  const getString = useFluent();
  const { loading, city } = useCurrentCity();
  const locations = useGlobalLocationData();
  const composition = useEconomicCompositionQuery({ year, cityId });
  const industryMap = useGlobalIndustryMap();

  if (
    loading ||
    locations.loading ||
    composition.loading
  ) {
    return <StandardSideTextLoading />;
  } else if (
    city &&
    locations.data &&
    composition.data &&
    composition.data.industries.length
  ) {
    const cityName = city.name ? city.name : "";
    const cityNamePlural = possessive([cityName]);
    const { countries } = locations.data;
    const { industries } = composition.data;
    const country = countries.find(
      (d) =>
        city.countryId !== null && d.countryId === city.countryId.toString(),
    );

    let total = 0;
    let totalEmploy = 0;
    const allSectors: IndustryDatum[] = [];
    industries.forEach(({ naicsId, numCompany, numEmploy }) => {
      const industry = industryMap.data[naicsId];
      const companies = numCompany ? numCompany : 0;
      const employees = numEmploy ? numEmploy : 0;
      const count =
        compositionType === CompositionType.Companies ? companies : employees;
      if (industry && industry.level !== null && industry.level <= DigitLevel.Sector) {
        total =
          compositionType === CompositionType.Companies
            ? total + companies
            : total + employees;
        totalEmploy = totalEmploy + employees;
        const { name, naicsIdTopParent } = industry;
        allSectors.push({
          count,
          name: name ? name : "",
          sector: naicsIdTopParent.toString(),
        });
      }
    });

    const largestSector: IndustryDatum | undefined = orderBy(
      allSectors,
      ["count"],
      ["desc"],
    )[0];
    if (!largestSector) {
      return <StandardSideTextLoading />;
    }

    const secondLargestSector: IndustryDatum | undefined = orderBy(
      allSectors,
      ["count"],
      ["desc"],
    )[1];
    if (!secondLargestSector) {
      return <StandardSideTextLoading />;
    }

    const title = getString("economic-composition-title", {
      "name-plural": cityNamePlural,
    });
    const para1 = getString("economic-composition-para-1", {
      name: cityName,
      "name-plural": cityNamePlural,
      "income-level": "",
      country: country ? country.nameShortEn : "",
      "pop-year": "2024",
      population: formatNumberLong(city.population ? city.population : 0),
      gdppc: formatNumberLong(city.gdppc ? city.gdppc : 0),
      "region-size-rank": ordinalNumber([1]),
      "region-wealth-rank": ordinalNumber([1]),
      "region-name": "",
      "region-city-count": 1,
      "num-employ": formatNumberLong(totalEmploy),
    });

    const para2 = getString("economic-composition-para-2", {
      name: cityName,
      "largest-sector": largestSector.name,
      "largest-sector-share-percent": parseFloat(
        ((largestSector.count / total) * 100).toFixed(2),
      ),
      "composition-type": compositionType,
      "largest-3-digit-industry-in-sector": largestSector.name,
      "largest-3-digit-industry-in-sector-share-percent": parseFloat(
        ((largestSector.count / total) * 100).toFixed(2),
      ),
      "second-largest-sector": secondLargestSector.name,
      "second-largest-sector-share-percent": parseFloat(
        ((secondLargestSector.count / total) * 100).toFixed(2),
      ),
      "second-largest-3-digit-industry-in-sector":
        secondLargestSector.name,
      "second-largest-3-digit-industry-in-sector-share-percent": parseFloat(
        ((secondLargestSector.count / total) * 100).toFixed(2),
      ),
    });

    return (
      <StandardSideTextBlock>
        <Helmet>
          <title>
            {title + " | " + getString("meta-data-title-default-suffix")}
          </title>
          <meta
            property="og:title"
            content={
              title + " | " + getString("meta-data-title-default-suffix")
            }
          />
        </Helmet>
        <ContentTitle>{title}</ContentTitle>
        <ContentParagraph>{para1}</ContentParagraph>
        <ContentParagraph>{para2}</ContentParagraph>
      </StandardSideTextBlock>
    );
  } else {
    return null;
  }
};

export default SideText;
