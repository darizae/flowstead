import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Select } from '@darizae/marisma';
import type { HistoryResponse } from '../../lib/api/types';
import { downloadBlob } from '../../lib/exports/download';
import { serializeHistoryCsv } from '../../lib/exports/csv';
import { historyCsvFileName, historyPngFileName } from '../../lib/exports/fileNames';
import { svgToPng } from '../../lib/exports/svgToPng';
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
  const svgRef = useRef<SVGSVGElement>(null);
  const mountedRef = useRef(true);
  const exportKeyRef = useRef('');
  const [pngDownloading, setPngDownloading] = useState(false);
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
  useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false; }; }, []);
  const exportKey = `${history.plant.plant_id}:${from}:${to}:${range}:${channel}`;
  exportKeyRef.current = exportKey;
  const downloadCsv = () => {
    downloadBlob(new Blob([serializeHistoryCsv(history, channel)], { type: 'text/csv;charset=utf-8' }), historyCsvFileName(history.plant, channel, range));
  };
  const downloadPng = async () => {
    const svg = svgRef.current;
    if (!svg || pngDownloading) return;
    const requestKey = exportKeyRef.current;
    setPngDownloading(true);
    try {
      const blob = await svgToPng(svg, {
        title: `${meta.axisLabel} — ${range}h — ${history.plant.name}`,
        legend: `Range: ${range} hours · Valid readings: ${points.length} · Missing/invalid readings shown as gaps · Timezone: ${history.plant.timezone}`,
      });
      if (mountedRef.current && requestKey === exportKeyRef.current) downloadBlob(blob, historyPngFileName(history.plant, channel, range));
    } finally {
      if (mountedRef.current) setPngDownloading(false);
    }
  };


  return <section className="history-chart" data-testid="history-chart" aria-labelledby="history-chart-title">
    <div className="history-controls">
      <div className="channel-control" role="group" aria-label="History channel">
        <span className="control-label">Channel</span>
        <div className="channel-buttons">{CHANNELS.map((item) => <Button key={item.key} type="button" size="small" variant={item.key === channel ? 'primary' : 'secondary'} aria-pressed={item.key === channel} onClick={() => onChannelChange(item.key)}>{item.label}</Button>)}</div>
      </div>
      <Select label="History range" value={String(range)} options={HISTORY_RANGES.map((value) => ({ value: String(value), label: value === 168 ? '7 days' : `${value} hours` }))} onValueChange={(value) => onRangeChange(Number(value) as HistoryRange)} />
    </div>
    <div className="chart-heading"><h3 id="history-chart-title">{meta.axisLabel}</h3></div>
    <p className="chart-status" aria-live="polite">Quality: valid values shown; missing and invalid readings are gaps.</p>
    {points.length === 0 && <p className="chart-empty" role="status">No valid readings in this window. Missing and invalid readings are shown as gaps.</p>}
    <div className="chart-scroll" ref={chartRef}><svg ref={svgRef} className="history-svg" viewBox={`0 0 ${chartWidth} ${HEIGHT}`} role="img" aria-labelledby="history-chart-title history-chart-description">
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
    <div className="chart-footer" data-testid="history-export-footer"><div className="chart-export-actions"><Button type="button" size="small" variant="secondary" onClick={downloadCsv}>Download CSV</Button><Button type="button" size="small" variant="secondary" onClick={() => void downloadPng()} disabled={pngDownloading}>{pngDownloading ? 'Preparing PNG…' : 'Download PNG'}</Button></div></div>
  </section>;
}
