import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiClient } from "../../lib/api/client";
import {
  ApiError,
  type ForecastJobResponse,
  type ForecastJobStatus,
} from "../../lib/api/types";
import { useRequestState } from "../../shared/hooks/useRequestState";

const POLL_DELAYS_MS = [250, 500, 1_000, 2_000, 2_000, 2_000, 2_000];

function sleep(ms: number): Promise<void> {
  const { promise, resolve } = Promise.withResolvers<void>();
  window.setTimeout(resolve, ms);
  return promise;
}

/**
 * Focused request-status polling (#68): reads the job until a terminal status,
 * the schedule is exhausted, or the caller's cancellation predicate fires.
 */
async function pollForecastRequest(
  client: ApiClient,
  correlationId: string,
  isCancelled: () => boolean,
): Promise<ForecastJobResponse> {
  let job: ForecastJobResponse = {
    request_event_id: "",
    correlation_id: correlationId,
    plant_id: "",
    status: "queued",
    requested_at_utc: "",
    completed_at_utc: null,
    diagnostic: null,
  };
  for (const delay of POLL_DELAYS_MS) {
    await sleep(delay);
    if (isCancelled()) break;
    job = await client.forecastRequest(correlationId);
    if (job.status === "completed" || job.status === "failed") break;
  }
  return job;
}

export function useForecastRequest(
  client: ApiClient,
  plantId: string | undefined,
  scopeKey: string,
  onCompleted: () => Promise<unknown>,
) {
  const [status, setStatus] = useState<ForecastJobStatus>();
  const generation = useRef(0);
  const { error, run } = useRequestState(false, "Unable to refresh forecast.");

  useEffect(() => {
    generation.current += 1;
    setStatus(undefined);
    return () => {
      generation.current += 1;
    };
  }, [plantId, scopeKey]);

  const refresh = useCallback(async () => {
    if (!plantId || scopeKey === "public") return;
    const request = ++generation.current;
    setStatus(undefined);
    const ok = await run(async () => {
      const job = await client.requestForecast(plantId);
      if (request !== generation.current) return;
      setStatus(job.status);
      const isCancelled = () => request !== generation.current;
      const finalJob = await pollForecastRequest(
        client,
        job.correlation_id,
        isCancelled,
      );
      if (isCancelled()) return;
      setStatus(finalJob.status);
      if (finalJob.status === "completed") {
        await onCompleted();
      } else if (finalJob.status === "failed") {
        throw new ApiError("http", "Forecast refresh failed.");
      } else {
        throw new ApiError("network", "Forecast refresh timed out. Try again.");
      }
    });
    if (ok === false) setStatus("failed");
  }, [client, onCompleted, plantId, run, scopeKey]);

  return { status, error, refresh };
}
