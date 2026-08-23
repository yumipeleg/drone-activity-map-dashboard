import { LatLngBoundsExpression } from 'leaflet';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';

/**
 * Bounds covering every given drone's coordinates, or `null` for an empty
 * list — kept as a pure function (no direct `L.Map` usage) so it's
 * testable without mounting Leaflet.
 */
export function computeBounds(drones: DroneTelemetry[]): LatLngBoundsExpression | null {
  if (drones.length === 0) {
    return null;
  }
  return drones.map((drone) => [drone.latitude, drone.longitude]);
}
