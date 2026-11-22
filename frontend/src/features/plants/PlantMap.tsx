import * as maplibregl from "maplibre-gl";
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { PlantSummary } from "../../lib/api/types";
import "maplibre-gl/dist/maplibre-gl.css";

maplibregl.setWorkerUrl(maplibreWorkerUrl);

const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const MAP_UNAVAILABLE_COPY = "Map unavailable. Select a plant from the list.";

function infoCard(plant: PlantSummary): HTMLElement {
  const card = document.createElement("span");
  card.className = "plant-marker-card";
  card.setAttribute("aria-hidden", "true");
  const data = [
    plant.name,
    `${plant.location.city}, ${plant.location.state_code}`,
    plant.timezone,
  ];
  data.forEach((line, i) => {
    const node = document.createElement(i === 0 ? "strong" : "span");
    node.textContent = line;
    card.appendChild(node);
  });
  return card;
}

export interface PlantMapProps {
  plants: PlantSummary[];
  onSelect: (plant: PlantSummary) => void;
  /** Optional immediately usable geographic preview during map loading/failure. */
  fallback?: ReactNode;
}

export function PlantMap({ plants, onSelect, fallback }: PlantMapProps) {
  const mapNode = useRef<HTMLDivElement>(null);
  const selectRef = useRef(onSelect);
  const [unavailable, setUnavailable] = useState(false);
  const [ready, setReady] = useState(false);
  const hasFallback = fallback !== undefined;
  selectRef.current = onSelect;
  useEffect(() => {
    if (!mapNode.current || plants.length === 0) return;
    let map: maplibregl.Map | undefined;
    const markers: maplibregl.Marker[] = [];
    let failed = false;
    let timeout: number | undefined;
    const failMap = () => {
      if (failed) return;
      failed = true;
      window.clearTimeout(timeout);
      markers.forEach((marker) => marker.remove());
      map?.remove();
      map = undefined;
      setUnavailable(true);
    };
    setUnavailable(false);
    setReady(false);
    try {
      const createdMap = new maplibregl.Map({
        container: mapNode.current,
        style: STYLE_URL,
        attributionControl: { compact: false },
        center: [-81.5, 27.5],
        zoom: 6,
      });
      map = createdMap;
      let styleLoaded = false;
      createdMap.once("load", () => {
        if (failed) return;
        styleLoaded = true;
        window.clearTimeout(timeout);
        setReady(true);
      });
      createdMap.on("error", () => {
        if (!styleLoaded) failMap();
      });
      // Some failed style requests never fire a MapLibre error. Keep the
      // geographic preview usable instead of leaving a blank map indefinitely.
      if (hasFallback) timeout = window.setTimeout(failMap, 12_000);
      const bounds = new maplibregl.LngLatBounds();
      for (const plant of plants) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "plant-marker";
        button.dataset.plantId = plant.plant_id;
        button.setAttribute("aria-label", `Open ${plant.name}`);
        button.title = plant.name;
        button.appendChild(infoCard(plant));
        button.addEventListener("click", () => selectRef.current(plant));
        markers.push(
          new maplibregl.Marker({ element: button })
            .setLngLat([plant.location.longitude, plant.location.latitude])
            .addTo(createdMap),
        );
        bounds.extend([plant.location.longitude, plant.location.latitude]);
      }
      if (!bounds.isEmpty())
        createdMap.fitBounds(bounds, { padding: 56, maxZoom: 10, duration: 0 });
    } catch {
      failMap();
    }
    return () => {
      window.clearTimeout(timeout);
      markers.forEach((marker) => marker.remove());
      map?.remove();
    };
  }, [plants, hasFallback]);

  if (hasFallback) {
    return (
      <div className="map-with-preview" data-testid="map-with-preview">
        {!unavailable && (
          <div
            className="real-map"
            ref={mapNode}
            role="region"
            aria-label="Map of visible Plants"
            aria-hidden={!ready}
            inert={!ready}
          />
        )}
        {(!ready || unavailable) && (
          <div className="map-preview-overlay">{fallback}</div>
        )}
      </div>
    );
  }
  if (unavailable)
    return (
      <div className="map-fallback" data-testid="map-fallback" role="status">
        <strong>{MAP_UNAVAILABLE_COPY}</strong>
      </div>
    );
  return (
    <div
      className="real-map"
      ref={mapNode}
      role="region"
      aria-label="Map of visible Plants"
    />
  );
}

export { MAP_UNAVAILABLE_COPY, STYLE_URL };
