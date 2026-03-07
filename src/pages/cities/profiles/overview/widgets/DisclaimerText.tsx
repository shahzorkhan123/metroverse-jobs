import React from "react";
import styled from "styled-components";
import useFluent from "../../../../../hooks/useFluent";
import { useStaticData } from "../../../../../dataProvider";

const Root = styled.small`
  text-align: center;
  font-size: 0.65rem;
  width: 100%;
  display: block;
`;

const DisclaimerText = () => {
  const getString = useFluent();
  const { loadedLevels, selectedYear } = useStaticData();

  return (
    <Root>
      <div>
        * {getString("city-overview-one-time-tooltip")} ({selectedYear})
      </div>
      <div>
        Loaded levels: {loadedLevels.join(", ")} — values are derived from static occupation records.
      </div>
    </Root>
  );
};

export default DisclaimerText;
