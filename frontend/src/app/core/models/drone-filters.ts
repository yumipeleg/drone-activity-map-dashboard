import { DroneStatus } from './drone-telemetry';

/**
 * Frontend-only shape for the optional `GET /api/drones` filters — not a
 * wire format itself, so camelCase is fine here. `query-params.ts` converts
 * this into the backend's snake_case query parameter names
 * (`drone_type`, `operator_id`, `min_battery`, `from`, `to`).
 */
export interface DroneFilters {
  droneType?: string;
  status?: DroneStatus;
  operatorId?: string;
  minBattery?: number;
  /** Calendar date, `yyyy-MM-dd` (inclusive start of range). */
  from?: string;
  /** Calendar date, `yyyy-MM-dd` (inclusive end of range). */
  to?: string;
}
