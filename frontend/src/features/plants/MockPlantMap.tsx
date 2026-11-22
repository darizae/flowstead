import type { PlantSummary } from '../../lib/api/types';

// Lightweight schematic for offline demo: avoids downloading map libraries or
// tiles. Labels and positions come from the same five generated Plant records.
export function MockPlantMap({ plants, onSelect }: { plants: PlantSummary[]; onSelect: (plant: PlantSummary) => void }) {
  return <div className="mock-map" aria-label="Schematic Florida plant locations">
    <span className="mock-map-heading">Florida · schematic preview</span>
    {plants.map((plant) => {
      const x = Math.min(86, Math.max(10, 20 + (plant.location.longitude + 83) * 35));
      const y = Math.min(82, Math.max(15, 15 + (29 - plant.location.latitude) * 16));
      return <button key={plant.plant_id} className="mock-map-pin" type="button"
        style={{ left: `${x}%`, top: `${y}%` }} onClick={() => onSelect(plant)}
        aria-label={`Open ${plant.name}`} title={plant.name}>
        <span aria-hidden="true" className="mock-map-dot" />{plant.location.city}
      </button>;
    })}
    <span className="mock-map-note">Illustrative placement · no live tiles or location tracking</span>
  </div>;
}