import { useEffect, useRef, useState } from "react";
import { downloadBlob } from "../../lib/exports/download";
import { svgToPng, type SvgToPngOptions } from "../../lib/exports/svgToPng";

export const CHART_WIDTH = 760;
export const CHART_HEIGHT = 300;
export const CHART_PADDING = { top: 22, right: 24, bottom: 66, left: 74 };
export const MOBILE_BREAKPOINT = 520;
export const MOBILE_PADDING = { top: 22, right: 14, bottom: 66, left: 72 };

export function niceDomain(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const low = Math.min(...values);
  const high = Math.max(...values);
  if (low === high) return [low - 1, high + 1];
  const pad = (high - low) * 0.08;
  return [low - pad, high + pad];
}

export function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function xPosition(
  timestamp: Date,
  fromMs: number,
  toMs: number,
  width: number,
  padding: typeof CHART_PADDING,
): number {
  return (
    padding.left +
    ((timestamp.getTime() - fromMs) / Math.max(1, toMs - fromMs)) *
      (width - padding.left - padding.right)
  );
}

export function yPosition(
  value: number,
  min: number,
  max: number,
  padding: typeof CHART_PADDING,
): number {
  return (
    CHART_HEIGHT -
    padding.bottom -
    ((value - min) / Math.max(1e-9, max - min)) *
      (CHART_HEIGHT - padding.top - padding.bottom)
  );
}

/** Tracks the rendered chart container width via ResizeObserver. */
export function useChartWidth() {
  const chartRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(CHART_WIDTH);
  useEffect(() => {
    const element = chartRef.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const updateWidth = (width: number) => {
      if (width > 0) setChartWidth(Math.round(width));
    };
    updateWidth(element.getBoundingClientRect().width);
    const observer = new ResizeObserver(([entry]) =>
      updateWidth(entry?.contentRect.width ?? 0),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return { chartRef, chartWidth };
}

/** Shared PNG export lifecycle: renders the current SVG and guards against stale/dismounted exports. */
export function usePngExport() {
  const svgRef = useRef<SVGSVGElement>(null);
  const mountedRef = useRef(true);
  const exportKeyRef = useRef("");
  const [pngDownloading, setPngDownloading] = useState(false);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);
  const downloadPng = async (options: SvgToPngOptions, fileName: string) => {
    const svg = svgRef.current;
    if (!svg || pngDownloading) return;
    const requestKey = exportKeyRef.current;
    setPngDownloading(true);
    try {
      const blob = await svgToPng(svg, options);
      if (mountedRef.current && requestKey === exportKeyRef.current)
        downloadBlob(blob, fileName);
    } finally {
      if (mountedRef.current) setPngDownloading(false);
    }
  };
  return { svgRef, exportKeyRef, pngDownloading, downloadPng };
}
