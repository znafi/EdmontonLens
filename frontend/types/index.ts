// TypeScript interfaces mirroring the FastAPI Pydantic response models.

export interface TransitRoute {
  route_id: string;
  route_short_name?: string | null;
  route_long_name?: string | null;
  route_type?: number | null;
}

export interface TransitStop {
  stop_id: string;
  stop_name?: string | null;
  stop_lat?: number | null;
  stop_lon?: number | null;
  neighbourhood_id?: string | null;
}

export interface PerformancePoint {
  route_id: string;
  service_date: string;
  on_time_rate: number;
  avg_delay_mins: number;
}

export interface StopDelay {
  stop_id: string;
  avg_delay_mins: number;
}

export interface DelayPrediction {
  route_id: string;
  delay_probability: number;
}

export interface Park {
  park_id: string;
  park_name?: string | null;
  neighbourhood_id?: string | null;
  park_type?: string | null;
  area_sqm?: number | null;
  amenities: string[];
  latitude?: number | null;
  longitude?: number | null;
}

export interface WasteSchedule {
  schedule_id: string;
  neighbourhood_id?: string | null;
  pickup_day?: string | null;
  waste_type?: string | null;
  biweekly?: boolean | null;
}

export interface DiversionRate {
  diversion_rate: number;
  recycling_organics_streams: number;
  total_streams: number;
}

export interface Neighbourhood {
  neighbourhood_id: string;
  neighbourhood_name?: string | null;
  area_sqkm?: number | null;
}

export interface NeighbourhoodSnapshot {
  neighbourhood_id: string;
  neighbourhood_name?: string | null;
  snapshot_date?: string | null;
  transit_stop_count?: number | null;
  avg_route_on_time?: number | null;
  park_count?: number | null;
  total_park_area_sqm?: number | null;
  waste_pickup_days?: number | null;
  transit_score?: number | null;
  park_score?: number | null;
  overall_score?: number | null;
}

export interface TrendPoint {
  snapshot_date: string;
  transit_score: number;
}

export interface AgentResponse {
  answer: string;
  sql_used: string;
  rows: Record<string, unknown>[];
}

export interface NeighbourhoodFeatureProperties {
  neighbourhood_id: string;
  neighbourhood_name?: string | null;
  overall_score: number;
  transit_score: number;
  park_score: number;
  park_count?: number | null;
  transit_stop_count?: number | null;
  waste_pickup_days?: number | null;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: NeighbourhoodFeatureProperties;
    geometry: GeoJSON.Geometry;
  }>;
}
