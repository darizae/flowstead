import type {
  ForecastHour as ContractForecastHour,
  ForecastJobResponse as ContractForecastJobResponse,
  ForecastResponse as ContractForecastResponse,
  HistoryReading as ContractHistoryReading,
  HistoryResponse as ContractHistoryResponse,
  LatestReading as ContractLatestReading,
  LatestResponse as ContractLatestResponse,
  Measurements as ContractMeasurements,
  PlantLinks as ContractPlantLinks,
  PlantListResponse as ContractPlantListResponse,
  PlantLocation as ContractPlantLocation,
  PlantSummary as ContractPlantSummary,
} from "./generated/types.gen";
import type {
  ForecastHour,
  ForecastJobResponse,
  ForecastResponse,
  HistoryReading,
  HistoryResponse,
  LatestReading,
  LatestResponse,
  Measurements,
  PlantLinks,
  PlantListResponse,
  PlantLocation,
  PlantSummary,
} from "./types";

/**
 * Audit #29: the hand-authored app-facing types in `./types` must not drift
 * from the backend OpenAPI contract. `generated/types.gen.ts` is produced from
 * the FastAPI Pydantic schemas (`pnpm run api:types`); these type-level
 * assertions fail the typecheck whenever the two contracts fall out of
 * structural compatibility — e.g. a renamed/removed field or a retyped property
 * breaks assignability in both directions, while deliberate width (branded
 * `ModelVersion`, broader unions, convenience optionals) remains compatible.
 */
type Compatible<A, B> = [A] extends [B] ? true : [B] extends [A] ? true : false;
type AssertCompatible<A, B> = Compatible<A, B> extends true ? true : never;

export const contractCompat: Readonly<Record<string, true>> = {
  plantLocation: true satisfies AssertCompatible<
    ContractPlantLocation,
    PlantLocation
  >,
  plantLinks: true satisfies AssertCompatible<ContractPlantLinks, PlantLinks>,
  plantSummary: true satisfies AssertCompatible<
    ContractPlantSummary,
    PlantSummary
  >,
  plantList: true satisfies AssertCompatible<
    ContractPlantListResponse,
    PlantListResponse
  >,
  latestReading: true satisfies AssertCompatible<
    ContractLatestReading,
    LatestReading
  >,
  latest: true satisfies AssertCompatible<
    ContractLatestResponse,
    LatestResponse
  >,
  historyReading: true satisfies AssertCompatible<
    ContractHistoryReading,
    HistoryReading
  >,
  history: true satisfies AssertCompatible<
    ContractHistoryResponse,
    HistoryResponse
  >,
  measurements: true satisfies AssertCompatible<
    ContractMeasurements,
    Measurements
  >,
  forecastHour: true satisfies AssertCompatible<
    Required<ContractForecastHour>,
    ForecastHour
  >,
  // The wire uses a plain model-version string; our application brands it
  // only after transport validation. Preserve every other field check.
  forecast: true satisfies AssertCompatible<
    ContractForecastResponse,
    Omit<ForecastResponse, "model_version"> & { model_version: string }
  >,
  forecastJob: true satisfies AssertCompatible<
    ContractForecastJobResponse,
    ForecastJobResponse
  >,
};
