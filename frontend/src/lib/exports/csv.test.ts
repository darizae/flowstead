import { describe, expect, it } from "vitest";
import {
  asModelVersion,
  type ForecastResponse,
  type HistoryResponse,
} from "../api/types";
import { serializeCsv, serializeForecastCsv, serializeHistoryCsv } from "./csv";

const plant = {
  plant_id: "plant-01",
  name: '=Unsafe, "Plant"',
  location: {
    city: "Test",
    state_code: "FL" as const,
    latitude: 27,
    longitude: -81,
  },
  timezone: "America/New_York",
  links: { latest: "", history: "", forecast: "" },
};
const measurements = (
  value: number | null,
  quality: "valid" | "missing" | "invalid",
) => ({
  influent_flow: { value, quality, units: "gal/h" as const },
  rainfall: {
    value: null,
    quality: "missing" as const,
    units: "in/h" as const,
  },
  dissolved_oxygen: {
    value: 2,
    quality: "valid" as const,
    units: "mg/L" as const,
  },
  effluent_ph: {
    value: 7,
    quality: "valid" as const,
    units: "unitless" as const,
  },
});

const history = {
  plant,
  from_utc: "2025-01-01T00:00:00.000Z",
  to_utc: "2025-01-01T03:00:00.000Z",
  readings: [
    {
      plant_id: "plant-01",
      timestamp_utc: "2025-01-01T02:00:00-05:00",
      latest: false as const,
      measurements: measurements(12.5, "valid"),
    },
    {
      plant_id: "plant-01",
      timestamp_utc: "2025-01-01T03:00:00Z",
      latest: false as const,
      measurements: measurements(null, "missing"),
    },
    {
      plant_id: "plant-01",
      timestamp_utc: "2025-01-01T04:00:00Z",
      latest: false as const,
      measurements: measurements(9, "invalid"),
    },
  ],
} satisfies HistoryResponse;

const forecast = {
  plant,
  status: "available" as const,
  issued_at_utc: "2025-01-01T00:00:00-05:00",
  model_version: asModelVersion("model,1"),
  source_revision: "revision",
  physical_bound_rule: "non-negative",
  forecasts: Array.from({ length: 12 }, (_, index) => ({
    hour_number: index + 1,
    target_time_utc: new Date(Date.UTC(2025, 0, 1, index + 1)).toISOString(),
    predicted_flow_gal_h: 100 + index,
    units: "gal/h" as const,
    source: "api",
  })),
  unavailable_reason: null,
} satisfies ForecastResponse;

describe("UT-M10-CSV", () => {
  it("serializes history with exact UTC, NULL values, quality, order, and formula defense", () => {
    const csv = serializeHistoryCsv(history, "influent_flow");
    expect(csv.split("\r\n")[0]).toBe(
      '"plant_id","plant_name","timestamp_utc","measurement","unit","value","quality"',
    );
    expect(csv).toContain(
      '"2025-01-01T07:00:00.000Z","influent_flow","gal/h","12.5","valid"',
    );
    expect(csv).toContain(
      '"2025-01-01T03:00:00.000Z","influent_flow","gal/h","","missing"',
    );
    expect(csv).toContain(
      '"2025-01-01T04:00:00.000Z","influent_flow","gal/h","9","invalid"',
    );
    expect(csv).toContain('"\'=Unsafe, ""Plant"""');
    expect(serializeCsv(["name"], [["\t=SUM(1,1)"]])).toContain(
      '"\'\t=SUM(1,1)"',
    );
  });

  it("serializes exactly twelve forecast targets with issue UTC, model, units, and formula-safe cells", () => {
    const csv = serializeForecastCsv(forecast);
    expect(csv.split("\r\n")).toHaveLength(14);
    expect(csv.split("\r\n")[0]).toBe(
      '"plant_id","plant_name","issue_time_utc","target_time_utc","measurement","unit","value","quality","model_version"',
    );
    expect(csv).toContain('"2025-01-01T05:00:00.000Z"');
    expect(csv).toContain(
      '"2025-01-01T01:00:00.000Z","influent_flow","gal/h","100","predicted","model,1"',
    );
  });

  it("SEC-M10-CSV neutralizes every spreadsheet formula-injection prefix", () => {
    // Excel/LibreOffice/Sheets treat a leading = + - @ (optionally after C0
    // controls / BOM) as a formula; the export must quote-prefix all of them.
    const prefixes = ["=", "+", "-", "@"];
    for (const prefix of prefixes) {
      expect(serializeCsv(["name"], [[`${prefix}cmd()|A0`]])).toContain(
        `"\'${prefix}cmd()|A0"`,
      );
      expect(serializeCsv(["name"], [[` \t${prefix}cmd()`]])).toContain(
        `"\' \t${prefix}cmd()"`,
      );
    }
    expect(serializeCsv(["name"], [["\r@x"]])).toContain('"\'\r@x"');
    expect(serializeCsv(["a", "b", "c"], [["normal", "1+1", "0=1"]])).toContain(
      '"normal","1+1","0=1"',
    );
  });

  it("rejects unbounded and malformed CSV rows", () => {
    expect(() =>
      serializeCsv(
        ["a"],
        Array.from({ length: 2 }, () => ["x"]),
        1,
      ),
    ).toThrow(/limited/);
    expect(() => serializeCsv(["a"], [["x", "y"]])).toThrow(/header width/);
  });
});
