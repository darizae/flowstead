import { Button, Card } from "@darizae/marisma";
import { useMemo } from "react";
import type { ForecastResponse } from "../../lib/api/types";
import { tryParseUtc } from "../../shared/domain/utc";
import { downloadBlob } from "../../lib/exports/download";
import { serializeForecastCsv } from "../../lib/exports/csv";
import {
  forecastCsvFileName,
  forecastPngFileName,
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
  FORECAST_HOURS,
  forecastPoints,
  fullForecastLabel,
  labelForecastPoints,
  type ForecastObservedPoint,
} from "./transforms";

const PADDING = { top: 26, right: 24, bottom: 66, left: 74 };

export interface ForecastChartProps {
  forecast: ForecastResponse;
  observed: ForecastObservedPoint[];
}

export function visibleForecastAxisTicks<T>(
  ticks: readonly T[],
  chartWidth: number,
): T[] {
  if (chartWidth > MOBILE_BREAKPOINT || ticks.length <= 3) return [...ticks];
  const middle = Math.floor(ticks.length / 2);
  return [ticks[0], ticks[middle], ticks[ticks.length - 1]];
}

export function ForecastChart({ forecast, observed }: ForecastChartProps) {
  const plant = forecast.plant;
  const points = useMemo(
    () => forecastPoints(forecast, observed),
    [forecast, observed],
  );
  const labeled = useMemo(
    () => labelForecastPoints(points, plant.timezone),
    [points, plant.timezone],
  );
  const { chartRef, chartWidth } = useChartWidth();
  const { svgRef, exportKeyRef, pngDownloading, downloadPng } = usePngExport();
  const padding = chartWidth <= MOBILE_BREAKPOINT ? MOBILE_PADDING : PADDING;
  const observedPoints = points.filter((point) => point.source === "observed");
  const predictedPoints = points.filter(
    (point) => point.source === "predicted",
  );
  const [min, max] = useMemo(
    () => niceDomain(points.map((point) => point.value)),
    [points],
  );

  const fromTime =
    points.length > 0
      ? points[0].timestampUtc.getTime()
      : forecast.issued_at_utc
        ? (tryParseUtc(forecast.issued_at_utc)?.getTime() ?? Number.NaN)
        : Number.NaN;
  const toTime =
    points.length > 0
      ? points[points.length - 1].timestampUtc.getTime()
      : fromTime + FORECAST_HOURS * 60 * 60 * 1000;
  const x = (timestamp: Date) =>
    xPosition(timestamp, fromTime, toTime, chartWidth, padding);
  const y = (value: number) => yPosition(value, min, max, padding);

  // Boundary is the first predicted point.
  const boundary = predictedPoints[0];
  const allAxisTicks = useMemo(() => {
    const anchor = Number.isFinite(fromTime) ? fromTime : Date.now();
    const end = Number.isFinite(toTime)
      ? toTime
      : anchor + FORECAST_HOURS * 60 * 60 * 1000;
    const step = (end - anchor) / 4;
    return Array.from(
      { length: 5 },
      (_, index) => new Date(anchor + step * index),
    );
  }, [fromTime, toTime]);
  const axisTicks = useMemo(
    () => visibleForecastAxisTicks(allAxisTicks, chartWidth),
    [allAxisTicks, chartWidth],
  );

  const yTicks = [0, 0.5, 1].map((fraction) => ({
    fraction,
    value: min + (max - min) * (1 - fraction),
  }));

  const heading = fullForecastLabel(forecast);
  const unavailable = forecast.status === "unavailable";
  const canExport =
    !unavailable &&
    forecast.forecasts.length === FORECAST_HOURS &&
    labeled.length > 0;
  const exportKey = `${plant.plant_id}:${forecast.issued_at_utc ?? ""}:${forecast.model_version}`;
  exportKeyRef.current = exportKey;
  const downloadCsv = () => {
    if (!canExport) return;
    downloadBlob(
      new Blob([serializeForecastCsv(forecast)], {
        type: "text/csv;charset=utf-8",
      }),
      forecastCsvFileName(plant),
    );
  };
  const downloadPngImage = () => {
    if (!canExport) return;
    void downloadPng(
      {
        title: `Influent flow forecast — ${plant.name}`,
        legend: `Observed · Predicted · Observed→predicted boundary · ${plant.timezone} · ${forecast.model_version}`,
      },
      forecastPngFileName(plant),
    );
  };

  return (
    <section
      className="forecast-chart"
      data-testid="forecast-chart"
      aria-labelledby="forecast-chart-title"
      role="status"
    >
      <div className="chart-heading">
        <h3 id="forecast-chart-title">Influent flow forecast</h3>
        <span className="forecast-status-issue" data-testid="forecast-issue">
          {heading}
        </span>
      </div>
      <p className="chart-status" aria-live="polite">
        {forecast.source_revision === "mock-only"
          ? "Preview only: synthetic browser-generated history and forecast, not API results."
          : "Observed readings merge into the 12-hour API forecast. Targets are API-predicted values, never client-computed."}
      </p>
      {unavailable ? (
        <Card
          className="forecast-unavailable"
          data-testid="forecast-unavailable"
        >
          <strong>Forecast unavailable</strong>
          <p>
            {forecast.unavailable_reason ??
              "No persisted forecast is available for this Plant yet."}
          </p>
          <span className="small-muted">
            Exactly {FORECAST_HOURS} API target hours are shown when available;
            none are invented client-side.
          </span>
        </Card>
      ) : labeled.length === 0 ? (
        <p className="chart-empty" role="status">
          No forecast targets are available for this Plant.
        </p>
      ) : (
        <div className="chart-scroll" ref={chartRef}>
          <svg
            ref={svgRef}
            className="forecast-svg"
            viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`}
            role="img"
            aria-labelledby="forecast-chart-title forecast-chart-description"
          >
            <desc id="forecast-chart-description">
              Influent flow observed-to-predicted boundary for {plant.name} in
              Plant-local time. {predictedPoints.length} API forecast targets.
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
            {observedPoints.length > 1 && (
              <polyline
                className="chart-line"
                points={observedPoints
                  .map((point) => `${x(point.timestampUtc)},${y(point.value)}`)
                  .join(" ")}
              />
            )}
            {predictedPoints.length > 1 && (
              <polyline
                className="chart-line forecast-predicted"
                points={predictedPoints
                  .map((point) => `${x(point.timestampUtc)},${y(point.value)}`)
                  .join(" ")}
              />
            )}
            {observedPoints.map((point) => (
              <circle
                key={point.timestampUtc.toISOString()}
                className="chart-point forecast-observed-point"
                cx={x(point.timestampUtc)}
                cy={y(point.value)}
                r="2.5"
                aria-label={`Observed: ${point.timestampUtc.toISOString()}`}
              >
                <title>{point.timestampUtc.toISOString()}</title>
              </circle>
            ))}
            {predictedPoints.map((point) => (
              <circle
                key={point.timestampUtc.toISOString()}
                className="chart-point forecast-target"
                cx={x(point.timestampUtc)}
                cy={y(point.value)}
                r="3"
                data-testid="forecast-target"
                aria-label={`Predicted ${point.value} gal/h`}
              >
                <title>{point.value} gal/h</title>
              </circle>
            ))}
            {boundary && (
              <line
                className="chart-boundary"
                x1={x(boundary.timestampUtc)}
                y1={padding.top}
                x2={x(boundary.timestampUtc)}
                y2={CHART_HEIGHT - padding.bottom}
              />
            )}
            {axisTicks.map((tick, index) => {
              const anchor =
                index === 0
                  ? "start"
                  : index === axisTicks.length - 1
                    ? "end"
                    : "middle";
              const tickX = xPosition(
                tick,
                fromTime,
                toTime,
                chartWidth,
                padding,
              );
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
                    {localTickLabel(tick, plant.timezone)}
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
              Influent flow (gal/h)
            </text>
          </svg>
        </div>
      )}
      <div className="quality-legend" aria-label="Forecast quality legend">
        <span>
          <i className="legend-swatch observed" />
          Observed
        </span>
        <span>
          <i className="legend-swatch predicted" />
          Predicted
        </span>
        <span>
          <i className="legend-swatch boundary" />
          Observed→predicted boundary
        </span>
        <span>
          {predictedPoints.length} of {FORECAST_HOURS} API targets
        </span>
      </div>
      <div className="chart-footer" data-testid="forecast-export-footer">
        <div className="chart-export-actions">
          <Button
            type="button"
            size="small"
            variant="secondary"
            onClick={downloadCsv}
            disabled={!canExport}
          >
            Download CSV
          </Button>
          <Button
            type="button"
            size="small"
            variant="secondary"
            onClick={downloadPngImage}
            disabled={!canExport || pngDownloading}
          >
            {pngDownloading ? "Preparing PNG…" : "Download PNG"}
          </Button>
        </div>
      </div>
    </section>
  );
}

function localTickLabel(timestamp: Date, timeZone: string): string {
  const labeled = labelForecastPoints(
    [{ timestampUtc: timestamp, value: 0, source: "observed" }],
    timeZone,
  )[0];
  return labeled.label.split(" ").slice(0, 2).join(" ");
}
