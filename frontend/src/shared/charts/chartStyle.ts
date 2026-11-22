/**
 * Single source for exported-SVG chart styling (#37). Mirrors the UI chart rules
 * in app.css (same selectors and colors) so exported PNGs cannot drift from the
 * on-screen charts. Keep both in sync when palette/typography changes.
 */
export const CHART_INLINE_STYLE = `
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
