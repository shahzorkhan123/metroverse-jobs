import React from "react";
import { DefaultContentWrapper } from "../../../../styling/GlobalGrid";
import TimeSeriesChart from "./TimeSeriesChart";
import useCurrentCityId from "../../../../hooks/useCurrentCityId";
import SimpleError from "../../../../components/transitionStateComponents/SimpleError";
import { LoadingOverlay } from "../../../../components/transitionStateComponents/VizLoadingBlock";

const TimeSeries = () => {
  const cityId = useCurrentCityId();

  if (cityId === null) {
    return (
      <DefaultContentWrapper>
        <LoadingOverlay>
          <SimpleError fluentMessageId={"global-ui-error-invalid-city"} />
        </LoadingOverlay>
      </DefaultContentWrapper>
    );
  }

  return (
    <DefaultContentWrapper>
      <TimeSeriesChart cityId={cityId} />
    </DefaultContentWrapper>
  );
};

export default TimeSeries;
