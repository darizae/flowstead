import { Suspense, lazy, useState } from "react";
import { Alert, Button, Card, PageHeading } from "@darizae/marisma";
import type { ApiError, PlantSummary } from "../../lib/api/types";
import { LoadingState, RetryButton } from "../../shared/components/Status";
import { PlantListRow } from "./components";
import { MockPlantMap } from "./MockPlantMap";
import "./plantsOverview.css";

const PlantMap = lazy(() =>
  import("./PlantMap").then((module) => ({ default: module.PlantMap })),
);

const PAGE_SIZE = 5;

export interface PlantsOverviewPageProps {
  plants: PlantSummary[];
  loading: boolean;
  error?: ApiError;
  retry: () => void;
  onSelect: (plant: PlantSummary) => void;
  mock?: boolean;
}

export function PlantsOverviewPage({
  plants,
  loading,
  error,
  retry,
  onSelect,
  mock = false,
}: PlantsOverviewPageProps) {
  const pageCount = Math.max(1, Math.ceil(plants.length / PAGE_SIZE));
  const [page, setPage] = useState(1);
  const current = Math.min(page, pageCount);
  const start = (current - 1) * PAGE_SIZE;
  const visible = plants.slice(start, start + PAGE_SIZE);
  return (
    <>
      <PageHeading
        className="page-head"
        eyebrow="Operations overview"
        title="Plants"
        description="Monitor the latest readings from wastewater Plants."
      />
      {loading ? (
        <LoadingState label="Loading Plants…" />
      ) : error ? (
        <Alert
          className="overview-alert"
          variant="danger"
          title={
            error.code === "unauthorized"
              ? "Session expired"
              : "Plants unavailable"
          }
          action={<RetryButton onClick={retry}>Retry</RetryButton>}
        >
          {error.message}
        </Alert>
      ) : plants.length === 0 ? (
        <Card className="surface empty">
          <strong>No plants assigned</strong>
          <span>There are no Plants available for this view.</span>
        </Card>
      ) : (
        <div className="overview-grid">
          <Card className="panel" aria-labelledby="plant-list-title">
            <div className="panel-head">
              <h2 id="plant-list-title">Plant list</h2>
              <span className="small-muted">
                {plants.length} {plants.length === 1 ? "Plant" : "Plants"}
              </span>
            </div>
            {visible.map((plant) => (
              <PlantListRow
                key={plant.plant_id}
                plant={plant}
                onSelect={() => onSelect(plant)}
              />
            ))}
            {pageCount > 1 && (
              <nav className="pagination" aria-label="Plant list pages">
                <Button
                  type="button"
                  variant="secondary"
                  size="small"
                  disabled={current === 1}
                  onClick={() => setPage(current - 1)}
                >
                  Previous
                </Button>
                <small aria-live="polite">
                  Showing {start + 1}–
                  {Math.min(start + PAGE_SIZE, plants.length)} of{" "}
                  {plants.length}
                </small>
                <Button
                  type="button"
                  variant="secondary"
                  size="small"
                  disabled={current === pageCount}
                  onClick={() => setPage(current + 1)}
                >
                  Next
                </Button>
              </nav>
            )}
          </Card>
          <Card className="panel map-panel" aria-labelledby="map-title">
            <div className="panel-head">
              <h2 id="map-title">Map View</h2>
            </div>
            <Suspense
              fallback={
                mock ? (
                  <MockPlantMap plants={plants} onSelect={onSelect} />
                ) : (
                  <p className="small-muted">Preparing map…</p>
                )
              }
            >
              <PlantMap
                plants={plants}
                onSelect={onSelect}
                fallback={
                  mock ? (
                    <MockPlantMap plants={plants} onSelect={onSelect} />
                  ) : undefined
                }
              />
            </Suspense>
          </Card>
        </div>
      )}
    </>
  );
}
