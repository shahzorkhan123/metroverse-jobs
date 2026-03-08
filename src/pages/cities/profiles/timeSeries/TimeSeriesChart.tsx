import React, { useState, useMemo, useCallback } from "react";
import styled from "styled-components/macro";
import { ContentGrid, primaryFont, backgroundMedium } from "../../../../styling/styleUtils";
import CategoryLabels from "../../../../components/dataViz/legend/CategoryLabels";
import { CategoryDatum } from "../../../../components/dataViz/legend/Label";
import useTimeSeriesData from "../../../../hooks/useTimeSeriesData";
import useGlobalLocationData from "../../../../hooks/useGlobalLocationData";
import { LoadingOverlay } from "../../../../components/transitionStateComponents/VizLoadingBlock";
import SimpleError from "../../../../components/transitionStateComponents/SimpleError";
import SideText from "./SideText";
import StackedAreaChart from "./StackedAreaChart";

const ControlsRow = styled.div`
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0;
  flex-wrap: wrap;
`;

const ControlLabel = styled.label`
  font-family: ${primaryFont};
  font-size: 0.8rem;
  color: #555;
  display: flex;
  align-items: center;
  gap: 0.4rem;
`;

const Select = styled.select`
  font-family: ${primaryFont};
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid ${backgroundMedium};
  border-radius: 3px;
  background: #fff;
`;

const ToggleGroup = styled.div`
  display: flex;
  border: 1px solid ${backgroundMedium};
  border-radius: 3px;
  overflow: hidden;
`;

const ToggleButton = styled.button<{ active: boolean }>`
  font-family: ${primaryFont};
  font-size: 0.8rem;
  padding: 0.25rem 0.75rem;
  border: none;
  background: ${({ active }) => (active ? "#333" : "#fff")};
  color: ${({ active }) => (active ? "#fff" : "#333")};
  cursor: pointer;

  &:hover {
    background: ${({ active }) => (active ? "#333" : "#eee")};
  }

  & + & {
    border-left: 1px solid ${backgroundMedium};
  }
`;

const ChartContainer = styled.div`
  grid-column: 1;
  grid-row: 2;
  min-height: 400px;
  position: relative;
`;

interface Props {
  cityId: string;
}

const TimeSeriesChart = ({ cityId }: Props) => {
  const locations = useGlobalLocationData();
  const {
    sources,
    selectedSourceId,
    setSelectedSourceId,
    selectedData,
    loading,
    error,
  } = useTimeSeriesData(cityId);

  const [metric, setMetric] = useState<"emp" | "gdp">("emp");
  const [hiddenCategories, setHiddenCategories] = useState<string[]>([]);

  // Find region name
  const regionName = useMemo(() => {
    if (!locations || !locations.data) return cityId;
    const region = locations.data.cities.find(
      (l) => l.id === cityId,
    );
    return region ? region.name || cityId : cityId;
  }, [locations, cityId]);

  // Toggle/isolate category handlers
  const toggleCategory = useCallback(
    (id: string) => {
      setHiddenCategories((prev) =>
        prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
      );
    },
    [],
  );

  const isolateCategory = useCallback(
    (id: string) => {
      if (!selectedData) return;
      const allIds = selectedData.groups.map((g) => g.id);
      setHiddenCategories(allIds.filter((c) => c !== id));
    },
    [selectedData],
  );

  const resetCategories = useCallback(() => {
    setHiddenCategories([]);
  }, []);

  // Build category labels for legend
  const categories = useMemo(() => {
    if (!selectedData) return [] as CategoryDatum[];
    return selectedData.groups.map((g) => ({
      id: g.id,
      name: g.name,
      color: g.color || "#999",
    })) as CategoryDatum[];
  }, [selectedData]);

  // Check if GDP is available
  const hasGdp = selectedData ? selectedData.metadata.hasGdp : false;

  // Filter sources based on region type
  const filteredSources = useMemo(() => {
    const isMetro = cityId.startsWith("metro-");
    return sources.filter((s) => {
      // ILOSTAT is national only
      if (isMetro && !s.hasMetro && s.id === "ilostat") return false;
      return true;
    });
  }, [sources, cityId]);

  if (loading && !selectedData) {
    return (
      <ContentGrid>
        <ControlsRow />
        <LoadingOverlay>
          <div>Loading time-series data...</div>
        </LoadingOverlay>
      </ContentGrid>
    );
  }

  if (error) {
    return (
      <ContentGrid>
        <ControlsRow />
        <SimpleError fluentMessageId={"global-ui-basic-data-error"} />
      </ContentGrid>
    );
  }

  if (!selectedData) {
    return (
      <ContentGrid>
        <ControlsRow>
          {filteredSources.length > 0 && (
            <ControlLabel>
              Source:
              <Select
                value={selectedSourceId || ""}
                onChange={(e) => setSelectedSourceId(e.target.value)}
              >
                {filteredSources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </ControlLabel>
          )}
        </ControlsRow>
        <ChartContainer>
          <p style={{ padding: "2rem", color: "#666" }}>
            No time-series data available for this region with the selected source.
          </p>
        </ChartContainer>
      </ContentGrid>
    );
  }

  return (
    <ContentGrid>
      <ControlsRow>
        {filteredSources.length > 1 && (
          <ControlLabel>
            Source:
            <Select
              value={selectedSourceId || ""}
              onChange={(e) => setSelectedSourceId(e.target.value)}
            >
              {filteredSources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </Select>
          </ControlLabel>
        )}
        <ControlLabel>
          Metric:
          <ToggleGroup>
            <ToggleButton
              active={metric === "emp"}
              onClick={() => setMetric("emp")}
            >
              Employment
            </ToggleButton>
            <ToggleButton
              active={metric === "gdp"}
              onClick={() => setMetric("gdp")}
              disabled={!hasGdp}
              style={!hasGdp ? { opacity: 0.4, cursor: "not-allowed" } : {}}
            >
              GDP
            </ToggleButton>
          </ToggleGroup>
        </ControlLabel>
        {filteredSources.length <= 1 && selectedData && (
          <ControlLabel style={{ marginLeft: "auto", color: "#888" }}>
            {selectedData.metadata.source} ({selectedData.metadata.years[0]}
            &ndash;
            {selectedData.metadata.years[selectedData.metadata.years.length - 1]})
          </ControlLabel>
        )}
      </ControlsRow>
      <ChartContainer>
        <StackedAreaChart
          data={selectedData}
          regionId={cityId}
          metric={metric}
          hiddenGroups={hiddenCategories}
          enableBrushZoom={selectedData.metadata.years.length > 15}
        />
      </ChartContainer>
      <SideText
        regionId={cityId}
        regionName={regionName}
        data={selectedData}
        metric={metric}
      />
      <CategoryLabels
        categories={categories}
        allowToggle={true}
        toggleCategory={toggleCategory}
        isolateCategory={isolateCategory}
        hiddenCategories={hiddenCategories}
        resetCategories={resetCategories}
        resetText={"Show all groups"}
      />
    </ContentGrid>
  );
};

export default TimeSeriesChart;
