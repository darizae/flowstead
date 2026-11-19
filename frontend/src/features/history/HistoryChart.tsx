import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Select } from '@darizae/marisma';
import type { HistoryResponse } from '../../lib/api/types';
import {
  CHANNELS, HISTORY_RANGES, chartTicks, channelMeta, labelHistoryPoints, qualitySegments,
  type ChannelKey, type HistoryRange,
} from './transforms';

const WIDTH = 760;
const HEIGHT = 300;
const PADDING = { top: 22, right: 24, bottom: 66, left: 74 };
const MOBILE_BREAKPOINT = 520;
const MOBILE_PADDING = { top: 22, right: 14, bottom: 66, left: 72 };

export interface HistoryChartProps {
  history: HistoryResponse;
  range: HistoryRange;
  channel: ChannelKey;
  onRangeChange: (range: HistoryRange) => void;
  onChannelChange: (channel: ChannelKey) => void;
}

function niceDomain(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const low = Math.min(...values);
  const high = Math.max(...values);
  if (low === high) return [low - 1, high + 1];
  const pad = (high - low) * 0.08;
  return [low - pad, high + pad];
}

function formatNumber(value: number): string { return Number.isInteger(value) ? String(value) : value.toFixed(2); }
const XML_ESCAPES: Record<string, string> = { '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' };
function escapeXml(value: string): string { return value.replace(/[<>&'"]/g, (character) => XML_ESCAPES[character] ?? character); }

function tickLabel(timestamp: string, history: HistoryResponse): { local: string; zone: string } {
  const label = labelHistoryPoints([{ timestampUtc: timestamp, value: 0, quality: 'valid' }], history.plant)[0];
  return {
    local: label.label.split(' ').slice(0, 2).join(' '),
    zone: `${label.timezoneAbbreviation} (${label.offset})`,
  };
}

function xPosition(timestamp: string, from: string, to: string, width: number, padding: typeof PADDING): number {
  return padding.left + ((Date.parse(timestamp) - Date.parse(from)) / Math.max(1, Date.parse(to) - Date.parse(from))) * (width - padding.left - padding.right);
}

export function HistoryChart({ history, range, channel, onRangeChange, onChannelChange }: HistoryChartProps) {
  const meta = channelMeta(channel);
  const segments = useMemo(() => qualitySegments(history.readings, channel), [history.readings, channel]);
  const points = useMemo(() => segments.flat(), [segments]);
  const [min, max] = useMemo(() => niceDomain(points.map((point) => point.value)), [points]);
  const chartRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(WIDTH);
  const from = history.from_utc;
  const to = history.to_utc;
  const padding = chartWidth <= MOBILE_BREAKPOINT ? MOBILE_PADDING : PADDING;
  const x = (timestamp: string) => xPosition(timestamp, from, to, chartWidth, padding);
  const y = (value: number) => HEIGHT - PADDING.bottom - ((value - min) / Math.max(1e-9, max - min)) * (HEIGHT - PADDING.top - PADDING.bottom);
  const allTicks = useMemo(() => chartTicks(range, from, to), [range, from, to]);
  const ticks = useMemo(() => {
    if (chartWidth > MOBILE_BREAKPOINT) return allTicks;
    const middle = Math.floor(allTicks.length / 2);
    return [allTicks[0], allTicks[middle], allTicks[allTicks.length - 1]];
  }, [allTicks, chartWidth]);
  const tickLabels = useMemo(() => ticks.map((tick) => tickLabel(tick, history)), [ticks, history]);
  const downloadTickLabels = useMemo(() => allTicks.map((tick) => tickLabel(tick, history)), [allTicks, history]);
  const yTicks = [0, 0.5, 1].map((fraction) => ({ fraction, value: min + (max - min) * (1 - fraction) }));
  const labels = labelHistoryPoints(points, history.plant);

  useEffect(() => {
    const element = chartRef.current;
    if (!element || typeof ResizeObserver === 'undefined') return;
    const updateWidth = (width: number) => {
      if (width > 0) setChartWidth(Math.round(width));
    };
    updateWidth(element.getBoundingClientRect().width);
    const observer = new ResizeObserver(([entry]) => updateWidth(entry?.contentRect.width ?? 0));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const downloadHref = useMemo(() => {
    const downloadX = (timestamp: string) => xPosition(timestamp, from, to, WIDTH, PADDING);
    const lines = [
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img">`,
      `<title>${escapeXml(meta.axisLabel)} — Plant-local time</title>`,
      `<desc>${escapeXml(meta.axisLabel)} over ${escapeXml(history.plant.name)} history. Missing and invalid readings remain gaps.</desc>`,
      '<style>text{font:12px sans-serif;fill:#183734}.axis{stroke:#54736c;stroke-width:1}.grid{stroke:#d5e1dc;stroke-width:1}.line{fill:none;stroke:#087968;stroke-width:2}.point{fill:#087968;stroke:#fff;stroke-width:1}</style>',
      `<line class="axis" x1="${PADDING.left}" y1="${HEIGHT - PADDING.bottom}" x2="${WIDTH - PADDING.right}" y2="${HEIGHT - PADDING.bottom}"/>`,
      `<line class="axis" x1="${PADDING.left}" y1="${PADDING.top}" x2="${PADDING.left}" y2="${HEIGHT - PADDING.bottom}"/>`,
      ...yTicks.flatMap(({ fraction, value }) => [
        `<line class="grid" x1="${PADDING.left}" y1="${PADDING.top + fraction * (HEIGHT - PADDING.top - PADDING.bottom)}" x2="${WIDTH - PADDING.right}" y2="${PADDING.top + fraction * (HEIGHT - PADDING.top - PADDING.bottom)}"/>`,
        `<text x="${PADDING.left - 10}" y="${PADDING.top + fraction * (HEIGHT - PADDING.top - PADDING.bottom) + 4}" text-anchor="end">${escapeXml(formatNumber(value))}</text>`,
      ]),
      ...segments.map((segment) => `<polyline class="line" points="${segment.map((point) => `${downloadX(point.timestampUtc)},${y(point.value)}`).join(' ')}"/>`),
      ...labels.map((point) => `<circle class="point" cx="${downloadX(point.timestampUtc)}" cy="${y(point.value)}" r="2.5"><title>${escapeXml(point.label)}</title></circle>`),
      ...allTicks.flatMap((tick, index) => {
        const anchor = index === 0 ? 'start' : index === allTicks.length - 1 ? 'end' : 'middle';
        const tickX = downloadX(tick);
        return [
          `<line class="axis" x1="${tickX}" y1="${HEIGHT - PADDING.bottom}" x2="${tickX}" y2="${HEIGHT - PADDING.bottom + 5}"/>`,
          `<text x="${tickX}" y="${HEIGHT - PADDING.bottom + 20}" text-anchor="${anchor}"><tspan x="${tickX}" dy="0">${escapeXml(downloadTickLabels[index].local)}</tspan><tspan x="${tickX}" dy="12">${escapeXml(downloadTickLabels[index].zone)}</tspan></text>`,
        ];
      }),
      `<text x="${WIDTH / 2}" y="${HEIGHT - 10}" text-anchor="middle">Plant-local time</text>`,
      `<text transform="translate(16 ${HEIGHT / 2}) rotate(-90)" text-anchor="middle">${escapeXml(meta.axisLabel)}</text>`,
      `<text x="${PADDING.left}" y="16">${escapeXml(meta.axisLabel)}</text>`,
      `<text x="${PADDING.left}" y="36">Timezone: ${escapeXml(history.plant.timezone)}</text>`,
      `<text x="${PADDING.left}" y="${HEIGHT - 2}">Missing/invalid readings shown as gaps · ${points.length} valid readings</text>`,
      '</svg>',
    ].join('');
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(lines)}`;
  }, [allTicks, downloadTickLabels, from, history, labels, meta.axisLabel, min, max, points.length, segments, to, yTicks]);

  return <section className="history-chart" data-testid="history-chart" aria-labelledby="history-chart-title">
    <div className="history-controls">
      <div className="channel-control" role="group" aria-label="History channel">
        <span className="control-label">Channel</span>
        <div className="channel-buttons">{CHANNELS.map((item) => <Button key={item.key} type="button" size="small" variant={item.key === channel ? 'primary' : 'secondary'} aria-pressed={item.key === channel} onClick={() => onChannelChange(item.key)}>{item.label}</Button>)}</div>
      </div>
      <Select label="History range" value={String(range)} options={HISTORY_RANGES.map((value) => ({ value: String(value), label: value === 168 ? '7 days' : `${value} hours` }))} onValueChange={(value) => onRangeChange(Number(value) as HistoryRange)} />
    </div>
    <div className="chart-heading"><h3 id="history-chart-title">{meta.axisLabel}</h3><a className="chart-download" href={downloadHref} download={`flowstead-${channel}-${range}h.svg`}>Download SVG</a></div>
    <p className="chart-status" aria-live="polite">Quality: valid values shown; missing and invalid readings are gaps.</p>
    {points.length === 0 && <p className="chart-empty" role="status">No valid readings in this window. Missing and invalid readings are shown as gaps.</p>}
    <div className="chart-scroll" ref={chartRef}><svg className="history-svg" viewBox={`0 0 ${chartWidth} ${HEIGHT}`} role="img" aria-labelledby="history-chart-title history-chart-description">
      <desc id="history-chart-description">{meta.axisLabel} over the selected period for {history.plant.name}. The horizontal axis is Plant-local time.</desc>
      <line className="chart-axis" x1={padding.left} y1={HEIGHT - padding.bottom} x2={chartWidth - padding.right} y2={HEIGHT - padding.bottom} />
      <line className="chart-axis" x1={padding.left} y1={padding.top} x2={padding.left} y2={HEIGHT - padding.bottom} />
      {yTicks.map(({ fraction, value }) => <g key={fraction}><line className="chart-grid" x1={padding.left} y1={padding.top + fraction * (HEIGHT - padding.top - padding.bottom)} x2={chartWidth - padding.right} y2={padding.top + fraction * (HEIGHT - padding.top - padding.bottom)} /><text className="chart-label" x={padding.left - 10} y={padding.top + fraction * (HEIGHT - padding.top - padding.bottom) + 4} textAnchor="end">{formatNumber(value)}</text></g>)}
      {segments.map((segment, index) => <polyline key={index} className="chart-line" points={segment.map((point) => `${x(point.timestampUtc)},${y(point.value)}`).join(' ')} />)}
      {labels.map((point) => <circle key={point.timestampUtc} className="chart-point" cx={x(point.timestampUtc)} cy={y(point.value)} r="2.5" aria-label={`${meta.axisLabel}: ${point.label}`}><title>{point.label}</title></circle>)}
      {ticks.map((tick, index) => { const anchor = index === 0 ? 'start' : index === ticks.length - 1 ? 'end' : 'middle'; const tickX = x(tick); return <g key={tick}><line className="chart-tick" x1={tickX} y1={HEIGHT - padding.bottom} x2={tickX} y2={HEIGHT - padding.bottom + 5} /><text className="chart-label chart-tick-label" x={tickX} y={HEIGHT - padding.bottom + 20} textAnchor={anchor}><tspan x={tickX} dy="0">{tickLabels[index].local}</tspan><tspan x={tickX} dy="12">{tickLabels[index].zone}</tspan></text></g>; })}
      <text className="chart-axis-title" x={chartWidth / 2} y={HEIGHT - 10} textAnchor="middle">Plant-local time</text>
      <text className="chart-axis-title" transform={`translate(16 ${HEIGHT / 2}) rotate(-90)`} textAnchor="middle">{meta.axisLabel}</text>
    </svg></div>
    <div className="quality-legend" aria-label="Chart quality legend"><span><i className="legend-swatch valid" />Valid</span><span><i className="legend-swatch gap" />Missing/invalid gap</span><span>{points.length} valid readings</span></div>
  </section>;
}
