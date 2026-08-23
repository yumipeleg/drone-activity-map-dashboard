import { DroneTelemetry } from '../../../core/models/drone-telemetry';

const ESCAPE_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

/** Escapes a string for safe interpolation into Leaflet's popup HTML (rendered via `innerHTML`). */
export function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ESCAPE_MAP[char]);
}

/**
 * Builds the marker popup content required by the exercise: Drone ID,
 * Drone type, Operator ID, Altitude, Speed, Battery percentage, Status,
 * and Last update timestamp. Kept as a pure function (no Leaflet
 * dependency) so it can be unit-tested directly.
 */
export function buildDronePopupHtml(drone: DroneTelemetry): string {
  const lastUpdate = new Date(drone.timestamp).toLocaleString();

  return `
    <div class="drone-popup">
      <strong>${escapeHtml(drone.drone_id)}</strong>
      <dl>
        <dt>Drone type</dt><dd>${escapeHtml(drone.drone_type)}</dd>
        <dt>Operator ID</dt><dd>${escapeHtml(drone.operator_id)}</dd>
        <dt>Altitude</dt><dd>${drone.altitude_m} m</dd>
        <dt>Speed</dt><dd>${drone.speed_kmh} km/h</dd>
        <dt>Battery</dt><dd>${drone.battery_percent}%</dd>
        <dt>Status</dt><dd>${escapeHtml(drone.status)}</dd>
        <dt>Last update</dt><dd>${escapeHtml(lastUpdate)}</dd>
      </dl>
    </div>
  `;
}
