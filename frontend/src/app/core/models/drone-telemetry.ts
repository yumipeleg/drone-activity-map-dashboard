/**
 * Mirrors the backend's `DroneTelemetryRead` response schema exactly
 * (backend/app/schemas/drone_telemetry.py). Field names stay snake_case —
 * this is the literal JSON shape FastAPI returns, and `HttpClient` does no
 * case conversion, so renaming them here would need a mapping layer for no
 * real benefit.
 */
export type DroneStatus = 'active' | 'landed' | 'lost_signal';

export interface DroneTelemetry {
  id: number;
  drone_id: string;
  drone_type: string;
  operator_id: string;
  latitude: number;
  longitude: number;
  altitude_m: number;
  speed_kmh: number;
  battery_percent: number;
  /** ISO 8601 timestamp string as sent by FastAPI; parsed to a Date only where needed for display. */
  timestamp: string;
  status: DroneStatus;
  created_at: string;
}
