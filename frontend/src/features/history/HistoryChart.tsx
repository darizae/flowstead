import { useMemo } from "react";
import { Button, Select } from "@darizae/marisma";
import type { HistoryResponse } from "../../lib/api/types";
import { parseUtcTimestamp } from "../../shared/domain/utc";
import { downloadBlob } from "../../lib/exports/download";
import { serializeHistoryCsv } from "../../lib/exports/csv";
import {
  historyCsvFileName,
  historyPngFileName,
} from "../../lib/exports/fileNames";
import {
  CHART_HEIGHT,
  MOBILE_BREAKPOINT,
  MOBILE_PADDING,
  formatNumber,
  niceDomain,
  useChartWidth,
  usePngExport,
  xPosition,
  yPosition,
} from "../../shared/charts/chart";
import {
  CHANNELS,
  HISTORY_RANGES,
  chartTicks,
  channelMeta,
  labelHistoryPoints,
  qualitySegments,
  type ChannelKey,
  type HistoryRange,
} from "./transforms";

const PADDING = { top: 22, right: 24, bottom: 66, left: 74 };

export interface HistoryChartProps {
  history: HistoryResponse;
  range: HistoryRange;
  channel: ChannelKey;
  onRangeChange: (range: HistoryRange) => void;
  onChannelChange: (channel: ChannelKey) => void;
}

function tickLabel(
  timestamp: Date,
  history: HistoryResponse,
): { local: string; zone: string } {
  const label = labelHistoryPoints(
    [{ timestampUtc: timestamp, value: 0, quality: "valid" }],
    history.plant,
  )[0];
  return {
    local: label.label.split(" ").slice(0, 2).join(" "),
    zone: `${label.timezoneAbbreviation} (${label.offset})`,
  };
}

export function HistoryChart({
  history,
  range,
  channel,
  onRangeChange,
  onChannelChange,
}: HistoryChartProps) {
  const meta = channelMeta(channel);
  const segments = useMemo(
    () => qualitySegments(history.readings, channel),
    [history.readings, channel],
  );
  const points = useMemo(() => segments.flat(), [segments]);
  const [min, max] = useMemo(
    () => niceDomain(points.map((point) => point.value)),
    [points],
  );
  const { chartRef, chartWidth } = useChartWidth();
  const { svgRef, exportKeyRef, pngDownloading, downloadPng } = usePngExport();
  const from = history.from_utc;
  const to = history.to_utc;
  const fromMs = parseUtcTimestamp(from, "window start").getTime();
  const toMs = parseUtcTimestamp(to, "window end").getTime();
  const padding = chartWidth <= MOBILE_BREAKPOINT ? MOBILE_PADDING : PADDING;
  const x = (timestamp: Date) =>
    xPosition(timestamp, fromMs, toMs, chartWidth, padding);
  const y = (value: number) => yPosition(value, min, max, padding);
  const allTicks = useMemo(
    () => chartTicks(range, from, to),
    [range, from, to],
  );
  const ticks = useMemo(() => {
    if (chartWidth > MOBILE_BREAKPOINT) return allTicks;
    const middle = Math.floor(allTicks.length / 2);
    return [allTicks[0], allTicks[middle], allTicks[allTicks.length - 1]];
  }, [allTicks, chartWidth]);
  const tickLabels = useMemo(
    () => ticks.map((tick) => tickLabel(tick, history)),
    [ticks, history],
  );
  const yTicks = [0, 0.5, 1].map((fraction) => ({
    fraction,
    value: min + (max - min) * (1 - fraction),
  }));
  const labels = labelHistoryPoints(points, history.plant);

  const exportKey = `${history.plant.plant_id}:${from}:${to}:${range}:${channel}`;
  exportKeyRef.current = exportKey;
  const downloadCsv = () => {
    downloadBlob(
      new Blob([serializeHistoryCsv(history, channel)], {
        type: "text/csv;charset=utf-8",
      }),
      historyCsvFileName(history.plant, channel, range),
    );
  };
  const downloadPngImage = () => {
    void downloadPng(
      {
        title: `${meta.axisLabel} — ${range}h — ${history.plant.name}`,
        legend: `Range: ${range} hours · Valid readings: ${points.length} · Missing/invalid readings shown as gaps · Timezone: ${history.plant.timezone}`,
      },
      historyPngFileName(history.plant, channel, range),
    );
  };

  return (
    <section
      className="history-chart"
      data-testid="history-chart"
      aria-labelledby="history-chart-title"
    >
      <div className="history-controls">
        <div
          className="channel-control"
          role="group"
          aria-label="History channel"
        >
          <span className="control-label">Channel</span>
          <div className="channel-buttons">
            {CHANNELS.map((item) => (
              <Button
                key={item.key}
                type="button"
                size="small"
                variant={item.key === channel ? "primary" : "secondary"}
                aria-pressed={item.key === channel}
                onClick={() => onChannelChange(item.key)}
              >
                {item.label}
              </Button>
            ))}
          </div>
        </div>
        <Select
          label="History range"
          value={String(range)}
          options={HISTORY_RANGES.map((value) => ({
            value: String(value),
            label: value === 168 ? "7 days" : `${value} hours`,
          }))}
          onValueChange={(value) =>
            onRangeChange(Number(value) as HistoryRange)
          }
        />
      </div>
      <div className="chart-heading">
        <h3 id="history-chart-title">{meta.axisLabel}</h3>
      </div>
      <p className="chart-status" aria-live="polite">
        Quality: valid values shown; missing and invalid readings are gaps.
      </p>
      {points.length === 0 && (
        <p className="chart-empty" role="status">
          No valid readings in this window. Missing and invalid readings are
          shown as gaps.
        </p>
      )}
      <div className="chart-scroll" ref={chartRef}>
        <svg
          ref={svgRef}
          className="history-svg"
          viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`}
          role="img"
          aria-labelledby="history-chart-title history-chart-description"
        >
          <desc id="history-chart-description">
            {meta.axisLabel} over the selected period for {history.plant.name}.
            The horizontal axis is Plant-local time.
          </desc>
          <line
            className="chart-axis"
            x1={padding.left}
            y1={CHART_HEIGHT - padding.bottom}
            x2={chartWidth - padding.right}
            y2={CHART_HEIGHT - padding.bottom}
          />
          <line
            className="chart-axis"
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={CHART_HEIGHT - padding.bottom}
          />
          {yTicks.map(({ fraction, value }) => (
            <g key={fraction}>
              <line
                className="chart-grid"
                x1={padding.left}
                y1={
                  padding.top +
                  fraction * (CHART_HEIGHT - padding.top - padding.bottom)
                }
                x2={chartWidth - padding.right}
                y2={
                  padding.top +
                  fraction * (CHART_HEIGHT - padding.top - padding.bottom)
                }
              />
              <text
                className="chart-label"
                x={padding.left - 10}
                y={
                  padding.top +
                  fraction * (CHART_HEIGHT - padding.top - padding.bottom) +
                  4
                }
                textAnchor="end"
              >
                {formatNumber(value)}
              </text>
            </g>
          ))}
          {segments.map((segment, index) => (
            <polyline
              key={index}
              className="chart-line"
              points={segment
                .map((point) => `${x(point.timestampUtc)},${y(point.value)}`)
                .join(" ")}
            />
          ))}
          {labels.map((point) => (
            <circle
              key={point.timestampUtc.toISOString()}
              className="chart-point"
              cx={x(point.timestampUtc)}
              cy={y(point.value)}
              r="2.5"
              aria-label={`${meta.axisLabel}: ${point.label}`}
            >
              <title>{point.label}</title>
            </circle>
          ))}
          {ticks.map((tick, index) => {
            const anchor =
              index === 0
                ? "start"
                : index === ticks.length - 1
                  ? "end"
                  : "middle";
            const tickX = x(tick);
            return (
              <g key={tick.toISOString()}>
                <line
                  className="chart-tick"
                  x1={tickX}
                  y1={CHART_HEIGHT - padding.bottom}
                  x2={tickX}
                  y2={CHART_HEIGHT - padding.bottom + 5}
                />
                <text
                  className="chart-label chart-tick-label"
                  x={tickX}
                  y={CHART_HEIGHT - padding.bottom + 20}
                  textAnchor={anchor}
                >
                  <tspan x={tickX} dy="0">
                    {tickLabels[index].local}
                  </tspan>
                  <tspan x={tickX} dy="12">
                    {tickLabels[index].zone}
                  </tspan>
                </text>
              </g>
            );
          })}
          <text
            className="chart-axis-title"
            x={chartWidth / 2}
            y={CHART_HEIGHT - 10}
            textAnchor="middle"
          >
            Plant-local time
          </text>
          <text
            className="chart-axis-title"
            transform={`translate(16 ${CHART_HEIGHT / 2}) rotate(-90)`}
            textAnchor="middle"
          >
            {meta.axisLabel}
          </text>
        </svg>
      </div>
      <div className="quality-legend" aria-label="Chart quality legend">
        <span>
          <i className="legend-swatch valid" />
          Valid
        </span>
        <span>
          <i className="legend-swatch gap" />
          Missing/invalid gap
        </span>
        <span>{points.length} valid readings</span>
      </div>
      <div className="chart-footer" data-testid="history-export-footer">
        <div className="chart-export-actions">
          <Button
            type="button"
            size="small"
            variant="secondary"
            onClick={downloadCsv}
          >
            Download CSV
          </Button>
          <Button
            type="button"
            size="small"
            variant="secondary"
            onClick={downloadPngImage}
            disabled={pngDownloading}
          >
            {pngDownloading ? "Preparing PNG…" : "Download PNG"}
          </Button>
        </div>
      </div>
    </section>
  );
}
