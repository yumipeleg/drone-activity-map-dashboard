import { DroneTelemetry } from './drone-telemetry';

/**
 * Mirrors the backend's `DroneTelemetryPage` envelope
 * (backend/app/schemas/drone_telemetry.py) returned by `GET /api/drones`.
 *
 * For the `latest_only=true` requests this dashboard always makes,
 * pagination is bypassed server-side: `items` contains every matching
 * drone's current row, and `total`/`page_size` both equal `items.length`.
 */
export interface DronePage {
  items: DroneTelemetry[];
  total: number;
  page: number;
  page_size: number;
}
