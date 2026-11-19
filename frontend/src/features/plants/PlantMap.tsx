import * as maplibregl from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { useEffect, useRef, useState } from 'react';
import type { PlantSummary } from '../../lib/api/types';
import 'maplibre-gl/dist/maplibre-gl.css';

maplibregl.setWorkerUrl(maplibreWorkerUrl);

const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';
const MAP_UNAVAILABLE_COPY = 'Map unavailable. Select a plant from the list.';

export interface PlantMapProps { plants: PlantSummary[]; onSelect: (plant: PlantSummary) => void }

export function PlantMap({ plants, onSelect }: PlantMapProps) {
  const mapNode = useRef<HTMLDivElement>(null);
  const selectRef = useRef(onSelect);
  const [unavailable, setUnavailable] = useState(false);
  selectRef.current = onSelect;
  useEffect(() => {
    if (!mapNode.current || plants.length === 0) return;
    let map: maplibregl.Map | undefined;
    const markers: maplibregl.Marker[] = [];
    let failed = false;
    const failMap = () => {
      if (failed) return;
      failed = true;
      markers.forEach((marker) => marker.remove());
      map?.remove();
      map = undefined;
      setUnavailable(true);
    };
    setUnavailable(false);
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
      createdMap.once('load', () => { styleLoaded = true; });
      createdMap.on('error', () => { if (!styleLoaded) failMap(); });
      const bounds = new maplibregl.LngLatBounds();
      for (const plant of plants) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'plant-marker';
        button.dataset.plantId = plant.plant_id;
        button.setAttribute('aria-label', `Open ${plant.name}`);
        button.title = plant.name;
        button.addEventListener('click', () => selectRef.current(plant));
        markers.push(new maplibregl.Marker({ element: button }).setLngLat([plant.location.longitude, plant.location.latitude]).addTo(createdMap));
        bounds.extend([plant.location.longitude, plant.location.latitude]);
      }
      if (!bounds.isEmpty()) createdMap.fitBounds(bounds, { padding: 56, maxZoom: 10, duration: 0 });
    } catch {
      failMap();
    }
    return () => {
      markers.forEach((marker) => marker.remove());
      map?.remove();
    };
  }, [plants]);

  if (unavailable) return <div className="map-fallback" data-testid="map-fallback" role="status"><strong>{MAP_UNAVAILABLE_COPY}</strong></div>;
  return <div className="real-map" ref={mapNode} role="region" aria-label="Map of visible Plants" />;
}

export { MAP_UNAVAILABLE_COPY, STYLE_URL };

