import React from "react";
import StandardSideTextBlock from "../../../../components/general/StandardSideTextBlock";
import {
  ContentParagraph,
  ContentTitle,
} from "../../../../styling/styleUtils";
import { TimeSeriesFile } from "../../../../dataProvider/types";
import { formatNumberLong } from "../../../../Utils";

interface Props {
  regionId: string;
  regionName: string;
  data: TimeSeriesFile;
  metric: "emp" | "gdp";
}

const SideText = ({ regionId, regionName, data, metric }: Props) => {
  const { years, source } = data.metadata;
  const regionData = data.data[regionId];

  if (!regionData || years.length < 2) {
    return (
      <StandardSideTextBlock>
        <ContentTitle>Time Series</ContentTitle>
        <ContentParagraph>
          No time-series data available for this region.
        </ContentParagraph>
      </StandardSideTextBlock>
    );
  }

  // Calculate growth for each group
  const firstIdx = 0;
  const lastIdx = years.length - 1;
  const growthByGroup: { id: string; name: string; growth: number; latestVal: number }[] = [];

  data.groups.forEach(group => {
    const gd = regionData[group.id];
    if (!gd) return;
    const series = metric === "gdp" && gd.gdp ? gd.gdp : gd.emp;
    const first = series[firstIdx];
    const last = series[lastIdx];
    if (first && last && first > 0) {
      growthByGroup.push({
        id: group.id,
        name: group.name,
        growth: ((last - first) / first) * 100,
        latestVal: last,
      });
    }
  });

  // Sort by growth
  const sorted = growthByGroup.slice().sort((a, b) => b.growth - a.growth);
  const fastest = sorted.slice(0, 3);
  const slowest = sorted.slice(-3).reverse();

  // Total change
  let totalFirst = 0;
  let totalLast = 0;
  data.groups.forEach(group => {
    const gd = regionData[group.id];
    if (!gd) return;
    const series = metric === "gdp" && gd.gdp ? gd.gdp : gd.emp;
    const first = series[firstIdx];
    const last = series[lastIdx];
    if (first) totalFirst += first;
    if (last) totalLast += last;
  });
  const totalGrowth = totalFirst > 0
    ? (((totalLast - totalFirst) / totalFirst) * 100).toFixed(1)
    : "N/A";

  const metricLabel = metric === "gdp" ? "GDP" : "employment";
  const yearRange = `${years[firstIdx]}\u2013${years[lastIdx]}`;

  return (
    <StandardSideTextBlock>
      <ContentTitle>
        {regionName}: Time Series
      </ContentTitle>
      <ContentParagraph>
        <strong>Source:</strong> {source} ({yearRange})
      </ContentParagraph>
      <ContentParagraph>
        Total {metricLabel} changed by <strong>{totalGrowth}%</strong> from{" "}
        {formatNumberLong(Math.round(totalFirst))} to{" "}
        {formatNumberLong(Math.round(totalLast))}.
      </ContentParagraph>
      {fastest.length > 0 && (
        <ContentParagraph>
          <strong>Fastest growing:</strong>{" "}
          {fastest.map(g =>
            `${g.name} (+${g.growth.toFixed(1)}%)`
          ).join(", ")}
        </ContentParagraph>
      )}
      {slowest.length > 0 && (
        <ContentParagraph>
          <strong>Slowest/declining:</strong>{" "}
          {slowest.map(g => {
            const sign = g.growth >= 0 ? "+" : "";
            return `${g.name} (${sign}${g.growth.toFixed(1)}%)`;
          }).join(", ")}
        </ContentParagraph>
      )}
    </StandardSideTextBlock>
  );
};

export default SideText;
