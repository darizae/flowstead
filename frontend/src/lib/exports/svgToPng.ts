export interface SvgToPngOptions {
  width?: number;
  title?: string;
  legend?: string;
}

const MIN_EXPORT_WIDTH = 1320;
const SVG_NS = 'http://www.w3.org/2000/svg';
const INLINE_STYLE = `
  text{font:12px Arial,sans-serif;fill:#183734}
  .chart-axis,.chart-tick{stroke:#526a67;stroke-width:1;fill:none}
  .chart-grid{stroke:#dce7e2;stroke-width:1;fill:none}
  .chart-line{fill:none;stroke:#087968;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}
  .chart-point{fill:#087968;stroke:#fff;stroke-width:1}
  .forecast-predicted{stroke:#07584c;stroke-dasharray:6 4}
  .chart-boundary{stroke:#07584c;stroke-width:1.5;stroke-dasharray:2 3;opacity:.75}
  .forecast-target{fill:#07584c}
  .forecast-observed-point{fill:#087968}
  .chart-label{fill:#526a67;font-size:11px}
  .chart-axis-title{fill:#183734;font-size:12px;font-weight:700}
  .chart-tick-label{font-size:10px}
  .export-title{font:700 18px Arial,sans-serif;fill:#183734}
  .export-legend{font:14px Arial,sans-serif;fill:#183734}
`;

function finiteNumber(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}
function wrapText(value: string, maxCharacters: number): string[] {
  const words = value.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = '';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (line && next.length > maxCharacters) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines.length > 0 ? lines : [''];
}

/** Rasterize the already-rendered chart SVG; no alternate chart data or renderer is used. */
export function svgToPng(svg: SVGSVGElement, options: SvgToPngOptions = {}): Promise<Blob> {
  if (typeof XMLSerializer === 'undefined') return Promise.reject(new Error('SVG export is unavailable.'));
  const source = svg.cloneNode(true) as SVGSVGElement;
  const viewBox = source.getAttribute('viewBox')?.trim().split(/[ ,]+/).map(Number) ?? [];
  const sourceWidth = finiteNumber(String(viewBox[2] ?? source.getAttribute('width')), 760);
  const sourceHeight = finiteNumber(String(viewBox[3] ?? source.getAttribute('height')), 300);
  const sourceViewBox = source.getAttribute('viewBox') ?? `0 0 ${sourceWidth} ${sourceHeight}`;
  const width = Math.max(MIN_EXPORT_WIDTH, Math.floor(options.width ?? MIN_EXPORT_WIDTH));
  const contentHeight = Math.max(1, Math.round(width * sourceHeight / sourceWidth));
  const titleLines = options.title ? wrapText(options.title, 120) : [];
  const legendLines = options.legend ? wrapText(options.legend, 150) : [];
  const titleBand = titleLines.length > 0 ? titleLines.length * 24 + 12 : 0;
  const legendBand = legendLines.length > 0 ? legendLines.length * 20 + 12 : 0;
  const height = titleBand + contentHeight + legendBand;

  const outer = document.createElementNS(SVG_NS, 'svg');
  outer.setAttribute('xmlns', SVG_NS);
  outer.setAttribute('viewBox', `0 0 ${width} ${height}`);
  outer.setAttribute('width', String(width));
  outer.setAttribute('height', String(height));
  outer.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  const style = document.createElementNS(SVG_NS, 'style');
  style.textContent = INLINE_STYLE;
  outer.append(style);

  const nested = document.createElementNS(SVG_NS, 'svg');
  nested.setAttribute('x', '0');
  nested.setAttribute('y', String(titleBand));
  nested.setAttribute('width', String(width));
  nested.setAttribute('height', String(contentHeight));
  nested.setAttribute('viewBox', sourceViewBox);
  nested.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  while (source.firstChild) nested.append(source.firstChild);
  outer.append(nested);

  if (titleLines.length > 0) {
    const title = document.createElementNS(SVG_NS, 'text');
    title.setAttribute('class', 'export-title');
    title.setAttribute('x', '16');
    title.setAttribute('y', '22');
    title.setAttribute('font-family', 'Arial, sans-serif');
    title.setAttribute('font-size', '18');
    title.setAttribute('font-weight', '700');
    titleLines.forEach((line, index) => {
      const tspan = document.createElementNS(SVG_NS, 'tspan');
      tspan.setAttribute('x', '16');
      tspan.setAttribute('dy', index === 0 ? '0' : '24');
      tspan.textContent = line;
      title.append(tspan);
    });
    outer.append(title);
  }
  if (legendLines.length > 0) {
    const legend = document.createElementNS(SVG_NS, 'text');
    legend.setAttribute('class', 'export-legend');
    legend.setAttribute('x', '16');
    legend.setAttribute('y', String(titleBand + contentHeight + 16));
    legend.setAttribute('font-family', 'Arial, sans-serif');
    legend.setAttribute('font-size', '14');
    legendLines.forEach((line, index) => {
      const tspan = document.createElementNS(SVG_NS, 'tspan');
      tspan.setAttribute('x', '16');
      tspan.setAttribute('dy', index === 0 ? '0' : '20');
      tspan.textContent = line;
      legend.append(tspan);
    });
    outer.append(legend);
  }

  const serialized = new XMLSerializer().serializeToString(outer);
  const svgBlob = new Blob([serialized], { type: 'image/svg+xml;charset=utf-8' });
  const objectUrl = URL.createObjectURL(svgBlob);
  return new Promise<Blob>((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext('2d');
        if (!context) throw new Error('PNG export is unavailable.');
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, width, height);
        context.drawImage(image, 0, 0, width, height);
        canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('PNG encoding failed.')), 'image/png');
      } catch (error) {
        reject(error instanceof Error ? error : new Error('PNG encoding failed.'));
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
    };
    image.onerror = () => { URL.revokeObjectURL(objectUrl); reject(new Error('SVG rasterization failed.')); };
    image.src = objectUrl;
  });
}


