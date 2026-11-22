import type { PlantSummary } from "../../lib/api/types";
import { FLORIDA_OUTLINE_PATH, floridaPoint } from "./floridaOutline";

// A geographic map is available even before MapLibre loads (or without WebGL,
// tiles, or the Oracle API). The coastline is real; all five sites are fictitious.
export function MockPlantMap({
  plants,
  onSelect,
}: {
  plants: PlantSummary[];
  onSelect: (plant: PlantSummary) => void;
}) {
  return (
    <div
      className="mock-map"
      role="region"
      aria-label="Geographic preview of mock Florida plants"
      data-testid="mock-geographic-map"
    >
      <svg
        className="mock-map-outline"
        viewBox="0 0 760 355"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path d={FLORIDA_OUTLINE_PATH} />
      </svg>
      <span className="mock-map-heading">Central &amp; Southwest Florida</span>
      <span className="mock-map-gulf" aria-hidden="true">
        Gulf of Mexico
      </span>
      <span className="mock-map-atlantic" aria-hidden="true">
        Atlantic Ocean
      </span>
      {plants.map((plant) => {
        const position = floridaPoint(
          plant.location.longitude,
          plant.location.latitude,
        );
        return (
          <button
            key={plant.plant_id}
            className="mock-map-pin"
            type="button"
            style={position}
            onClick={() => onSelect(plant)}
            aria-label={`Open ${plant.name}`}
            title={plant.name}
          >
            <span aria-hidden="true" className="mock-map-dot" />
            {plant.location.city}
          </button>
        );
      })}
      <span className="mock-map-note">
        Coastline: U.S. Census · Fictional plant locations
      </span>
    </div>
  );
}
