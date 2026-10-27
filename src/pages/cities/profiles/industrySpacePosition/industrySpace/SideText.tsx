import React from "react";
import styled from "styled-components/macro";
import { useHistory } from "react-router-dom";
import queryString from "query-string";
import StandardSideTextBlock from "../../../../../components/general/StandardSideTextBlock";
import {
  ContentParagraph,
  ContentTitle,
  primaryColor,
  primaryColorDark,
  lightBorderColor,
  primaryFont,
} from "../../../../../styling/styleUtils";
import { possessive } from "../../../../../hooks/useFluent";
import useFluent from "../../../../../hooks/useFluent";
import useCurrentCity from "../../../../../hooks/useCurrentCity";
import useQueryParams from "../../../../../hooks/useQueryParams";
import StandardSideTextLoading from "../../../../../components/transitionStateComponents/StandardSideTextLoading";
import {
  useCurrentSpaceType,
  useComplexityData,
  useSpaceLayout,
} from "../../../../../hooks/useSpaceData";
import { SpaceType } from "../../../../../routing/routes";
import Helmet from "react-helmet";

export const taskComplexityArticleHref =
  process.env.PUBLIC_URL +
  "/analysis/task-complexity-analysis/task-complexity-analysis.html";

const Toggle = styled.div`
  display: flex;
  margin: 0.5rem 0 1rem;
  border: solid 1px ${lightBorderColor};
  width: fit-content;
`;

const ToggleButton = styled.button<{ $selected: boolean }>`
  font-family: ${primaryFont};
  font-size: 0.8rem;
  padding: 0.35rem 0.75rem;
  border: none;
  cursor: pointer;
  background-color: ${({ $selected }) => ($selected ? primaryColor : "#fff")};
  color: ${({ $selected }) => ($selected ? "#fff" : primaryColorDark)};
`;

const Stats = styled.p`
  font-size: 0.75rem;
  color: #666;
  margin: 0 0 0.75rem;
`;

const ArticleLink = styled.a`
  display: inline-block;
  font-size: 0.85rem;
  font-weight: 600;
  color: ${primaryColorDark};
  margin-bottom: 1rem;
`;

const description = {
  [SpaceType.occupation]: (
    <>
      Each dot is an occupation. Two occupations are linked when US metro
      areas tend to specialise in both at the same time (both have a relative
      presence above 1), the same way the Atlas of Economic Complexity builds
      its Product Space from exports. Occupations that sit close together
      draw on similar local know-how, so a region is more likely to grow
      occupations near the ones it already has. Grey dots are occupations
      with a relative presence below 1 in this region.
    </>
  ),
  [SpaceType.job]: (
    <>
      Each dot is an occupation. Two occupations are linked when they share
      many of the same work activities in O*NET (Detailed Work Activities). It
      is a propensity graph for workers: neighbouring jobs need similar tasks,
      so skills transfer more easily between them. Grey dots are occupations
      with a relative presence below 1 in this region.
    </>
  ),
};

const SideText = ({ children }: { children: React.ReactNode }) => {
  const getString = useFluent();
  const history = useHistory();
  const params = useQueryParams();
  const { loading, city } = useCurrentCity();
  const spaceType = useCurrentSpaceType();
  const { data: complexity } = useComplexityData();
  const { data: layout } = useSpaceLayout();

  const setSpace = (value: SpaceType) => {
    const query = queryString.stringify({ ...params, space: value });
    history.push(history.location.pathname + "?" + query);
  };

  if (loading) {
    return <StandardSideTextLoading />;
  } else if (city) {
    const cityName = city.name ? city.name : "";
    const spaceName =
      spaceType === SpaceType.job ? "Job Space" : "Occupation Space";
    const title = `What is ${possessive([cityName])} position in the ${spaceName}?`;

    let eciText: React.ReactElement<any> | null = null;
    if (complexity && city.cityId && complexity.eci[city.cityId] !== undefined) {
      const eci = complexity.eci[city.cityId];
      const ranked = Object.values(complexity.eci).sort((a, b) => b - a);
      const rank = ranked.indexOf(eci) + 1;
      eciText = (
        <ContentParagraph>
          Regional complexity (ECI): <strong>{eci.toFixed(2)}</strong>, ranked{" "}
          {rank} of {ranked.length} metro areas.
        </ContentParagraph>
      );
    }

    return (
      <StandardSideTextBlock>
        <Helmet>
          <title>
            {title + " | " + getString("meta-data-title-default-suffix")}
          </title>
          <meta
            property="og:title"
            content={title + " | " + getString("meta-data-title-default-suffix")}
          />
        </Helmet>
        <ContentTitle>{title}</ContentTitle>
        <Toggle>
          <ToggleButton
            $selected={spaceType === SpaceType.occupation}
            onClick={() => setSpace(SpaceType.occupation)}
          >
            Occupation Space
          </ToggleButton>
          <ToggleButton
            $selected={spaceType === SpaceType.job}
            onClick={() => setSpace(SpaceType.job)}
          >
            Job Space (tasks)
          </ToggleButton>
        </Toggle>
        <ContentParagraph>{description[spaceType]}</ContentParagraph>
        {eciText}
        {layout ? (
          <Stats>
            {layout.stats.nNodes} occupations · {layout.stats.nLinks} links ·{" "}
            {layout.stats.nContinents} high- and {layout.stats.nCountries}{" "}
            low-aggregation knowledge clusters
          </Stats>
        ) : null}
        <ArticleLink
          href={taskComplexityArticleHref}
          target="_blank"
          rel="noopener noreferrer"
        >
          How is complexity computed? Read the Task Complexity Analysis →
        </ArticleLink>
        {children}
      </StandardSideTextBlock>
    );
  } else {
    return null;
  }
};

export default SideText;
