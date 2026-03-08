import React, { useRef, useEffect, useCallback } from "react";
import * as d3 from "d3";
import styled from "styled-components/macro";
import {
  getStandardTooltip,
  RapidTooltipRoot,
} from "../../../../utilities/rapidTooltip";
import { TimeSeriesFile } from "../../../../dataProvider/types";

/* ── Styled ────────────────────────────────────── */

const Root = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
`;

/* ── Types ─────────────────────────────────────── */

interface GroupDef {
  id: string;
  name: string;
  color: string;
}

export interface Props {
  data: TimeSeriesFile;
  regionId: string;
  metric: "emp" | "gdp";
  hiddenGroups: string[];
  enableBrushZoom?: boolean;
}

/* ── Helpers ───────────────────────────────────── */

const MARGIN = { top: 12, right: 20, bottom: 30, left: 70 };

function formatLargeNumber(n: number): string {
  if (n >= 1e12) return (n / 1e12).toFixed(1) + "T";
  if (n >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toFixed(0);
}

function formatFullNumber(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatPct(n: number): string {
  return n.toFixed(1) + "%";
}

/* ── Component ─────────────────────────────────── */

const StackedAreaChart = ({ data, regionId, metric, hiddenGroups, enableBrushZoom }: Props) => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const draw = useCallback(() => {
    const svgEl = svgRef.current;
    const container = containerRef.current;
    if (!svgEl || !container) return;

    const regionData = data.data[regionId];
    if (!regionData) return;

    const years = data.metadata.years;
    const visibleGroups: GroupDef[] = data.groups
      .filter(g => !hiddenGroups.includes(g.id))
      .map(g => ({ id: g.id, name: g.name, color: g.color || "#999" }));
    const groupIds = visibleGroups.map(g => g.id);

    // Build tabular data: one row per year
    const rows = years.map((year, idx) => {
      const row: any = { year };
      visibleGroups.forEach(g => {
        const gd = regionData[g.id];
        if (!gd) { row[g.id] = 0; return; }
        const series = metric === "gdp" && gd.gdp ? gd.gdp : gd.emp;
        row[g.id] = series[idx] != null ? series[idx] : 0;
      });
      return row;
    });

    // Dimensions
    const rect = container.getBoundingClientRect();
    const width = rect.width || 700;
    const height = 420;
    const innerW = width - MARGIN.left - MARGIN.right;
    const innerH = height - MARGIN.top - MARGIN.bottom;

    // Clear
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    // Clip path
    svg.append("defs").append("clipPath")
      .attr("id", "ts-clip")
      .append("rect")
      .attr("width", innerW)
      .attr("height", innerH);

    const g = svg.append("g").attr("transform", `translate(${MARGIN.left},${MARGIN.top})`);

    // Scales
    const x = d3.scaleLinear()
      .domain(d3.extent(years) as [number, number])
      .range([0, innerW]);
    const stack = d3.stack().keys(groupIds).order(d3.stackOrderReverse);
    const stacked = stack(rows);
    const yMax = d3.max(stacked, layer => d3.max(layer, d => d[1])) || 0;
    const y = d3.scaleLinear().domain([0, yMax * 1.05]).range([innerH, 0]);

    // Color map
    const colorMap: Record<string, string> = {};
    visibleGroups.forEach(g => { colorMap[g.id] = g.color; });

    // Area generator
    const areaGen = d3.area<any>()
      .x(d => x(d.data.year) as number)
      .y0(d => y(d[0]) as number)
      .y1(d => y(d[1]) as number)
      .curve(d3.curveMonotoneX);

    // Draw areas
    const chartArea = g.append("g").attr("clip-path", "url(#ts-clip)");
    chartArea.selectAll("path.ts-area")
      .data(stacked)
      .enter()
      .append("path")
      .attr("class", "ts-area")
      .attr("d", areaGen)
      .attr("fill", d => colorMap[d.key] || "#999")
      .attr("opacity", 0.85);

    // X axis
    const xAxis = g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x).ticks(Math.min(years.length, 12)).tickFormat(d => String(d)));

    // Y axis (starts from 0)
    g.append("g")
      .call(d3.axisLeft(y).ticks(8).tickFormat(d => formatLargeNumber(d as number)));

    // Gridlines
    g.append("g")
      .attr("class", "grid")
      .call(d3.axisLeft(y).ticks(8).tickSize(-innerW).tickFormat(() => ""))
      .selectAll("line")
      .attr("stroke", "#e0e0e0")
      .attr("stroke-dasharray", "2,2");
    g.select(".grid .domain").remove();

    // ── Tooltip (attached to SVG, not clipped area, so it works with brush) ──
    const tooltipNode = tooltipRef.current;

    // Vertical hover line (inside clipped area for visual)
    const hoverLine = chartArea.append("line")
      .attr("class", "ts-hover-line")
      .attr("y1", 0).attr("y2", innerH)
      .attr("stroke", "#333").attr("stroke-width", 1)
      .attr("stroke-dasharray", "3,3")
      .style("display", "none");

    // Attach mouse events to SVG directly — avoids brush overlay conflict
    svg.on("mousemove", function () {
        const [rawX, rawY] = d3.mouse(this as any);
        const chartX = rawX - MARGIN.left;
        const chartY = rawY - MARGIN.top;

        // Outside chart area — hide tooltip
        if (chartX < 0 || chartX > innerW || chartY < 0 || chartY > innerH) {
          hoverLine.style("display", "none");
          if (tooltipNode) tooltipNode.style.display = "none";
          return;
        }

        const yearRaw = x.invert(chartX);
        const yearIdx = d3.bisector((d: number) => d).left(years, yearRaw);
        const idx = Math.max(0, Math.min(years.length - 1,
          yearIdx > 0 && yearRaw - years[yearIdx - 1] < years[yearIdx] - yearRaw
            ? yearIdx - 1 : yearIdx));
        const year = years[idx];

        const xPos = x(year) as number;
        hoverLine.attr("x1", xPos).attr("x2", xPos).style("display", null);

        if (!tooltipNode) return;

        // Compute totals for percentages
        let totalEmp = 0;
        let totalGdp = 0;
        visibleGroups.forEach(grp => {
          const gd = regionData[grp.id];
          if (!gd) return;
          const empVal = gd.emp[idx];
          if (empVal != null) totalEmp += empVal;
          if (gd.gdp) {
            const gdpVal = gd.gdp[idx];
            if (gdpVal != null) totalGdp += gdpVal;
          }
        });

        // Find which layer the mouse is in
        const yVal = y.invert(chartY);
        let hoveredGroupId = "";
        for (let i = stacked.length - 1; i >= 0; i--) {
          const layer = stacked[i];
          if (layer[idx] && yVal >= layer[idx][0] && yVal <= layer[idx][1]) {
            hoveredGroupId = layer.key;
            break;
          }
        }

        // Build tooltip rows
        const tooltipRows: string[][] = [];
        const source = data.metadata.source;
        tooltipRows.push(["Source", `${source} ${year}`]);
        tooltipRows.push(["", ""]);  // spacer

        visibleGroups.forEach(grp => {
          const gd = regionData[grp.id];
          if (!gd) return;
          const empVal = gd.emp[idx] || 0;
          const gdpVal = gd.gdp ? (gd.gdp[idx] || 0) : 0;
          const empPct = totalEmp > 0 ? (empVal / totalEmp) * 100 : 0;
          const avgIncome = empVal > 0 && gdpVal > 0 ? gdpVal / empVal : 0;

          if (grp.id === hoveredGroupId) {
            tooltipRows.push([`\u25B6 ${grp.name}`, ""]);
            tooltipRows.push(["  Employment", formatFullNumber(empVal)]);
            tooltipRows.push(["  % of Total", formatPct(empPct)]);
            if (avgIncome > 0) {
              tooltipRows.push(["  Avg Income", "$" + formatFullNumber(Math.round(avgIncome))]);
            }
            if (gdpVal > 0) {
              const gdpPct = totalGdp > 0 ? (gdpVal / totalGdp) * 100 : 0;
              tooltipRows.push(["  GDP Contrib.", formatLargeNumber(gdpVal)]);
              tooltipRows.push(["  % of GDP", formatPct(gdpPct)]);
            }
          }
        });

        if (!hoveredGroupId) {
          tooltipRows.push(["Total Employment", formatFullNumber(totalEmp)]);
          if (totalGdp > 0) {
            tooltipRows.push(["Total GDP", formatLargeNumber(totalGdp)]);
          }
        }

        const hoveredGroup = visibleGroups.find(vg => vg.id === hoveredGroupId);
        const color = hoveredGroup ? hoveredGroup.color : "#555";
        const title = hoveredGroup ? hoveredGroup.name : `Year ${year}`;

        tooltipNode.innerHTML = getStandardTooltip({
          title,
          color,
          rows: tooltipRows,
          boldColumns: [0],
        });
        tooltipNode.style.display = "block";

        // Position tooltip near the mouse
        const svgRect = svgEl.getBoundingClientRect();
        const tooltipW = tooltipNode.offsetWidth || 200;
        let tooltipLeft = svgRect.left + MARGIN.left + xPos;
        const tooltipTop = svgRect.top + MARGIN.top + chartY;
        // Keep on screen
        if (tooltipLeft + tooltipW / 2 > window.innerWidth) {
          tooltipLeft = window.innerWidth - tooltipW / 2 - 10;
        }
        if (tooltipLeft - tooltipW / 2 < 0) {
          tooltipLeft = tooltipW / 2 + 10;
        }
        tooltipNode.style.left = tooltipLeft + "px";
        tooltipNode.style.top = tooltipTop + "px";
      })
      .on("mouseleave", function () {
        hoverLine.style("display", "none");
        if (tooltipNode) {
          tooltipNode.style.display = "none";
        }
      });

    // ── Brush zoom (optional) ─────────────────
    if (enableBrushZoom && years.length > 10) {
      const brush = d3.brushX()
        .extent([[0, 0], [innerW, innerH]])
        .on("end", function () {
          const sel = d3.brushSelection(this as any) as [number, number] | null;
          if (!sel) return;
          const [x0, x1] = sel.map(x.invert as any);
          x.domain([x0, x1]);
          chartArea.selectAll("path.ts-area")
            .transition().duration(300)
            .attr("d", areaGen);
          xAxis.transition().duration(300)
            .call(d3.axisBottom(x).ticks(Math.min(12, Math.round(x1 - x0))).tickFormat(d => String(d)) as any);
          chartArea.select(".ts-brush").call(brush.move as any, null);
        });

      chartArea.append("g")
        .attr("class", "ts-brush")
        .call(brush);
    }
  }, [data, regionId, metric, hiddenGroups, enableBrushZoom]);

  // Draw on mount + deps change
  useEffect(() => {
    draw();
    const handleResize = () => draw();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [draw]);

  return (
    <Root ref={containerRef}>
      <svg ref={svgRef} />
      <RapidTooltipRoot ref={tooltipRef} />
    </Root>
  );
};

export default StackedAreaChart;
