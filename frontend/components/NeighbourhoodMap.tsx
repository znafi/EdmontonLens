"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import type L from "leaflet";
import type { Layer } from "leaflet";
import type { Feature, Geometry } from "geojson";
import { client } from "@/lib/api";
import type { GeoJSONFeatureCollection, NeighbourhoodFeatureProperties } from "@/types";

interface Props {
  onSelect?: (id: string) => void;
  /** When set, the map flies to this neighbourhood and opens its popup. */
  flyToId?: string | null;
  /** Called once the fly-to animation finishes so the parent can reset flyToId. */
  onFlown?: () => void;
}

/** Inner component that lives inside MapContainer and can call useMap(). */
function FlyToController({
  flyToId,
  layersRef,
  onFlown,
}: {
  flyToId?: string | null;
  layersRef: React.MutableRefObject<Map<string, Layer>>;
  onFlown?: () => void;
}) {
  const map = useMap();
  useEffect(() => {
    if (!flyToId) return;
    const layer = layersRef.current.get(flyToId) as L.Polygon | undefined;
    if (!layer) return;
    const bounds = layer.getBounds?.();
    if (bounds) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }
    setTimeout(() => {
      (layer as unknown as { openPopup?: () => void }).openPopup?.();
      onFlown?.();
    }, 350);
    // flyToId is intentionally the only dep — we want this to fire on every
    // new value, including re-selecting the same neighbourhood after reset.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyToId]);
  return null;
}

// Choropleth colour scale by overall_score (0-10).
function colorForScore(score: number): string {
  if (score >= 8) return "#15803d";
  if (score >= 6) return "#65a30d";
  if (score >= 4) return "#eab308";
  if (score >= 2) return "#ea580c";
  return "#dc2626";
}

const LEGEND = [
  { label: "8 to 10", color: "#15803d" },
  { label: "6 to 8",  color: "#65a30d" },
  { label: "4 to 6",  color: "#eab308" },
  { label: "2 to 4",  color: "#ea580c" },
  { label: "0 to 2",  color: "#dc2626" },
];

export default function NeighbourhoodMap({ onSelect, flyToId, onFlown }: Props) {
  const [data, setData] = useState<GeoJSONFeatureCollection | null>(null);
  const layersRef = useRef<Map<string, Layer>>(new Map());

  useEffect(() => {
    client.geojson().then(setData).catch(() => setData(null));
  }, []);

  function styleFeature(feature?: Feature<Geometry, NeighbourhoodFeatureProperties>) {
    const score = feature?.properties?.overall_score ?? 0;
    return {
      fillColor: colorForScore(score),
      weight: 1,
      opacity: 1,
      color: "#ffffff",
      fillOpacity: 0.65,
    };
  }

  function onEachFeature(
    feature: Feature<Geometry, NeighbourhoodFeatureProperties>,
    layer: Layer,
  ) {
    const p = feature.properties;
    layersRef.current.set(p.neighbourhood_id, layer);
    layer.bindPopup(
      `<div style="min-width:180px;line-height:1.6">
        <strong style="font-size:14px">${p.neighbourhood_name ?? p.neighbourhood_id}</strong><br/>
        <span style="color:#475569;font-size:12px">Overall score: <strong>${p.overall_score?.toFixed(1) ?? "-"}/10</strong></span><br/>
        <span style="color:#475569;font-size:12px">Transit score: ${p.transit_score?.toFixed(1) ?? "-"} &nbsp;(${p.transit_stop_count ?? 0} stops)</span><br/>
        <span style="color:#475569;font-size:12px">Park score: ${p.park_score?.toFixed(1) ?? "-"} &nbsp;(${p.park_count ?? 0} parks)</span><br/>
        <span style="color:#475569;font-size:12px">Waste pickups/mo: ${p.waste_pickup_days ?? 0}</span><br/>
        <a href="/neighbourhood?id=${p.neighbourhood_id}"
           style="color:#1d4ed8;font-weight:600;font-size:12px">See full breakdown</a>
      </div>`,
    );
    layer.on("click", () => onSelect?.(p.neighbourhood_id));
  }

  return (
    <div className="relative h-full w-full">
      <MapContainer center={[53.5461, -113.4938]} zoom={11} scrollWheelZoom className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {data && (
          <GeoJSON
            key={data.features.length}
            data={data as unknown as GeoJSON.GeoJsonObject}
            style={styleFeature as never}
            onEachFeature={onEachFeature as never}
          />
        )}
        <FlyToController flyToId={flyToId} layersRef={layersRef} onFlown={onFlown} />
      </MapContainer>

      <div className="absolute bottom-4 right-4 z-[400] rounded-lg bg-white/95 p-3 text-xs shadow-md">
        <p className="mb-1 font-semibold text-slate-700">Overall score</p>
        {LEGEND.map((l) => (
          <div key={l.label} className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: l.color }} />
            <span className="text-slate-600">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
