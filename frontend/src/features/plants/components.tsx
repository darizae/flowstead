import { Button, Card, PageHeading, Select } from "@darizae/marisma";
import type {
  Measurement,
  Measurements,
  PlantSummary,
} from "../../lib/api/types";

export const METRIC_ORDER = [
  ["influent_flow", "Influent flow", "gal/h"],
  ["rainfall", "Rainfall", "in/h"],
  ["dissolved_oxygen", "Dissolved oxygen", "mg/L"],
  ["effluent_ph", "Effluent pH", "unitless"],
] as const satisfies ReadonlyArray<[keyof Measurements, string, string]>;

export function PlantListRow({
  plant,
  onSelect,
}: {
  plant: PlantSummary;
  onSelect: () => void;
}) {
  return (
    <Button
      className="plant-row"
      variant="secondary"
      fullWidth
      type="button"
      onClick={onSelect}
    >
      <span>
        <strong>{plant.name}</strong>
        <small>
          {plant.location.city}, {plant.location.state_code}
        </small>
      </span>
      <span aria-hidden="true" className="arrow">
        →
      </span>
    </Button>
  );
}

export function PlantDetailHeader({
  plant,
  plants,
  onBack,
  onSwitch,
  onDownload,
  downloadDisabled,
  downloadLoading,
}: {
  plant: PlantSummary;
  plants: PlantSummary[];
  onBack: () => void;
  onSwitch: (plantId: string) => void;
  onDownload: () => void;
  downloadDisabled: boolean;
  downloadLoading: boolean;
}) {
  return (
    <PageHeading
      className="detail-header"
      eyebrow="Plant details"
      title={plant.name}
      description={`${plant.location.city}, Florida · ${plant.timezone}`}
      breadcrumbs={
        <Button
          className="back-link"
          variant="ghost"
          size="small"
          type="button"
          onClick={onBack}
        >
          ← <span>All plants</span>
        </Button>
      }
      actions={
        <div className="detail-actions">
          <Button
            type="button"
            variant="secondary"
            size="small"
            onClick={onDownload}
            disabled={downloadDisabled || downloadLoading}
          >
            {downloadLoading ? "Preparing PDF…" : "Download PDF"}
          </Button>
          <Select
            label="Select plant"
            value={plant.plant_id}
            options={plants.map((item) => ({
              value: item.plant_id,
              label: item.name,
            }))}
            onValueChange={onSwitch}
          />
        </div>
      }
    />
  );
}

function measurementCopy(measurement: Measurement): {
  value: string;
  status: string;
} {
  if (measurement.quality === "missing" || measurement.value === null)
    return { value: "—", status: "Missing" };
  if (measurement.quality === "invalid")
    return { value: "—", status: "Invalid" };
  return {
    value: measurement.value.toLocaleString(undefined, {
      maximumFractionDigits: 2,
    }),
    status: "Valid",
  };
}

export function MetricCards({ measurements }: { measurements: Measurements }) {
  return (
    <div className="metrics" aria-label="Latest measurements">
      {METRIC_ORDER.map(([key, label, unit]) => {
        const copy = measurementCopy(measurements[key]);
        return (
          <Card className="metric-card" key={key}>
            <p>{label}</p>
            <strong>
              {copy.value} <small>{copy.value === "—" ? "" : unit}</small>
            </strong>
            <span>
              {copy.status}
              {copy.value === "—" ? ` · ${unit}` : ""}
            </span>
          </Card>
        );
      })}
    </div>
  );
}
