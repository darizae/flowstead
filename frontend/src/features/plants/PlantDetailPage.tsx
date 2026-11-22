import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Card } from "@darizae/marisma";
import type { ApiClient } from "../../lib/api/client";
import {
  ApiError,
  type HistoryReading,
  type LatestResponse,
  type PlantSummary,
} from "../../lib/api/types";
import { parseUtcTimestamp } from "../../shared/domain/utc";
import { downloadBlob } from "../../lib/exports/download";
import { LoadingState, RetryButton } from "../../shared/components/Status";
import { HistoryChart } from "../history/HistoryChart";
import { type ChannelKey, type HistoryRange } from "../history/transforms";
import { usePlantHistory } from "../history/usePlantHistory";
import { ForecastChart } from "../forecast/ForecastChart";
import { type ForecastObservedPoint } from "../forecast/transforms";
import { usePlantForecast } from "../forecast/usePlantForecast";
import { useForecastRequest } from "../forecast/useForecastRequest";
import { MetricCards, PlantDetailHeader } from "./components";

export interface PlantDetailPageProps {
  client: ApiClient;
  selectedPlant?: PlantSummary;
  plants: PlantSummary[];
  loading: boolean;
  listError?: ApiError;
  latest?: LatestResponse;
  detailLoading: boolean;
  detailError?: ApiError;
  onBack: () => void;
  onSwitch: (plantId: string) => void;
  retry: () => void;
  scopeKey: string;
}

/** Recent valid observed influent-flow points for the observed→predicted boundary. */
function observedFromHistory(
  readings: HistoryReading[] | undefined,
): ForecastObservedPoint[] {
  if (!readings) return [];
  return readings
    .filter(
      (reading) =>
        reading.measurements.influent_flow.quality === "valid" &&
        reading.measurements.influent_flow.value !== null,
    )
    .map((reading) => ({
      reading,
      timestamp: parseUtcTimestamp(reading.timestamp_utc, "reading timestamp"),
    }))
    .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
    .slice(-12)
    .map(({ reading, timestamp }) => ({
      timestampUtc: timestamp,
      value: reading.measurements.influent_flow.value as number,
    }));
}

export function PlantDetailPage({
  client,
  selectedPlant,
  plants,
  loading,
  listError,
  latest,
  detailLoading,
  detailError,
  onBack,
  onSwitch,
  retry,
  scopeKey,
}: PlantDetailPageProps) {
  const [range, setRange] = useState<HistoryRange>(24);
  const [channel, setChannel] = useState<ChannelKey>("influent_flow");
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | undefined>();
  const scopeRef = useRef(scopeKey);
  const plantRef = useRef(selectedPlant?.plant_id);
  const mountedRef = useRef(true);
  const history = usePlantHistory(
    client,
    selectedPlant?.plant_id,
    range,
    scopeKey,
    latest?.reading.timestamp_utc,
  );
  const forecast = usePlantForecast(client, selectedPlant?.plant_id, scopeKey);
  const observed = useMemo(
    () => observedFromHistory(history.history?.readings),
    [history.history],
  );
  const forecastRequest = useForecastRequest(
    client,
    selectedPlant?.plant_id,
    scopeKey,
    forecast.retry,
  );
  scopeRef.current = scopeKey;
  plantRef.current = selectedPlant?.plant_id;
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);
  if (loading) return <LoadingState label="Loading Plant…" />;
  const download = () => {
    if (
      !selectedPlant ||
      !latest ||
      loading ||
      listError ||
      detailLoading ||
      detailError ||
      downloadLoading
    )
      return;
    const requestedScope = scopeKey;
    const requestedPlant = selectedPlant.plant_id;
    setDownloadLoading(true);
    setDownloadError(undefined);
    void client
      .downloadReport(requestedPlant)
      .then(({ blob, fileName }) => {
        if (
          mountedRef.current &&
          scopeRef.current === requestedScope &&
          plantRef.current === requestedPlant
        )
          downloadBlob(blob, fileName);
      })
      .catch((error: unknown) => {
        if (mountedRef.current && scopeRef.current === requestedScope)
          setDownloadError(
            error instanceof ApiError
              ? error.message
              : "Report download failed.",
          );
      })
      .finally(() => {
        if (mountedRef.current && scopeRef.current === requestedScope)
          setDownloadLoading(false);
      });
  };
  if (listError?.code === "unauthorized")
    return (
      <div className="error-state" role="alert">
        <strong>Session expired</strong>
        <p>Your authorized Plant list is no longer available.</p>
        <RetryButton onClick={onBack}>All plants</RetryButton>
      </div>
    );
  if (!selectedPlant)
    return (
      <Card className="surface state">
        <strong>Plant not available</strong>
        <p>This Plant is not available in your current view.</p>
        <RetryButton onClick={onBack}>All plants</RetryButton>
      </Card>
    );
  const reportDisabled =
    scopeKey === "mock:public" ||
    loading ||
    Boolean(listError) ||
    detailLoading ||
    Boolean(detailError) ||
    !latest;
  return (
    <>
      <PlantDetailHeader
        plant={selectedPlant}
        plants={plants}
        onBack={onBack}
        onSwitch={onSwitch}
        onDownload={download}
        downloadDisabled={reportDisabled}
        downloadLoading={downloadLoading}
      />
      {downloadError && (
        <p className="error-state" role="alert">
          {downloadError}
        </p>
      )}
      {detailLoading ? (
        <LoadingState label="Loading latest measurements…" />
      ) : detailError ? (
        <div className="error-state" role="alert">
          <strong>
            {detailError.code === "plant_not_found"
              ? "Plant not available"
              : detailError.code === "unauthorized"
                ? "Session expired"
                : "Latest readings unavailable"}
          </strong>
          <p>
            {detailError.code === "plant_not_found"
              ? "This Plant is not available in your current view."
              : detailError.message}
          </p>
          <RetryButton
            onClick={detailError.code === "plant_not_found" ? onBack : retry}
          >
            {detailError.code === "plant_not_found" ? "All plants" : "Retry"}
          </RetryButton>
        </div>
      ) : latest ? (
        <>
          <MetricCards measurements={latest.reading.measurements} />
          <div className="detail-grid">
            <Card className="history-panel" aria-labelledby="history-title">
              <h2 id="history-title">Measurement history</h2>
              {history.loading ? (
                <LoadingState label="Loading history…" />
              ) : history.error ? (
                <div className="error-state" role="alert">
                  <strong>History unavailable</strong>
                  <p>{history.error.message}</p>
                  <RetryButton onClick={history.retry}>Retry</RetryButton>
                </div>
              ) : history.history ? (
                <HistoryChart
                  history={history.history}
                  range={range}
                  channel={channel}
                  onRangeChange={setRange}
                  onChannelChange={setChannel}
                />
              ) : (
                <p>No history is available for this Plant.</p>
              )}
            </Card>
            <Card className="forecast-panel" aria-labelledby="forecast-title">
              <div className="forecast-panel-head">
                <h2 id="forecast-title">Influent flow forecast</h2>
                {client.hasPrincipal ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="small"
                    data-testid="forecast-refresh"
                    disabled={
                      forecastRequest.status === "queued" ||
                      forecastRequest.status === "processing"
                    }
                    onClick={() => void forecastRequest.refresh()}
                  >
                    Refresh forecast
                  </Button>
                ) : null}
              </div>
              {forecastRequest.status ? (
                <p
                  className={`forecast-request-status ${forecastRequest.status === "failed" ? "error" : ""}`}
                  data-testid="forecast-request-status"
                  role="status"
                >
                  {forecastRequest.status === "queued"
                    ? "Forecast queued"
                    : forecastRequest.status === "processing"
                      ? "Forecast processing"
                      : forecastRequest.status === "completed"
                        ? "Forecast completed"
                        : (forecastRequest.error?.message ??
                          "Forecast refresh failed.")}
                </p>
              ) : null}
              {forecast.loading ? (
                <LoadingState label="Loading forecast…" />
              ) : forecast.error ? (
                <div className="error-state" role="alert">
                  <strong>Forecast unavailable</strong>
                  <p>{forecast.error.message}</p>
                  <RetryButton onClick={forecast.retry}>Retry</RetryButton>
                </div>
              ) : forecast.forecast ? (
                <ForecastChart
                  forecast={forecast.forecast}
                  observed={observed}
                />
              ) : (
                <p>No forecast is available for this Plant.</p>
              )}
            </Card>
          </div>
        </>
      ) : (
        <Card className="surface state">
          <strong>Latest readings unavailable</strong>
          <p>Try again to load this Plant.</p>
          <RetryButton onClick={retry}>Retry</RetryButton>
        </Card>
      )}
    </>
  );
}
