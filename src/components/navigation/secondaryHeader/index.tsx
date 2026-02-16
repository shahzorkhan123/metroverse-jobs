import React from "react";
import { SecondaryHeaderContainer } from "../../../styling/GlobalGrid";
import styled from "styled-components/macro";
import {
  backgroundMedium,
  defaultPadding,
} from "../../../styling/styleUtils";
import { UtilityBarPortal } from "./UtilityBar";
import { columnsToRowsBreakpoint } from "../Utils";
import CitySearch from "./CitySearch";
import { Route, Switch } from "react-router-dom";
import { CityRoutes } from "../../../routing/routes";

const Root = styled(SecondaryHeaderContainer)`
  background-color: ${backgroundMedium};
  padding: 0.4rem ${defaultPadding}rem;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 1fr auto;
  grid-gap: 0.7rem;
  pointer-events: auto;
  min-height: 40px;

  @media (max-width: 1100px) {
    padding: 0.55rem;
  }

  @media (max-width: ${columnsToRowsBreakpoint}px) {
    grid-template-columns: auto;
    grid-rows-columns: auto auto;
    padding-bottom: 0.45rem;
    min-height: 83px;
  }
`;

const SecondaryHeader = () => {
  return (
    <Root>
      <Switch>
        <Route path={CityRoutes.CityBase} component={CitySearch} />
      </Switch>
      <UtilityBarPortal />
    </Root>
  );
};

export default SecondaryHeader;
