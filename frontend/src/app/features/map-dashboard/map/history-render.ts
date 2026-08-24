import { CircleMarkerOptions, PolylineOptions } from 'leaflet';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import { getHistoryPointStyle } from './history-point-style';

const PATH_STYLE: PolylineOptions = { color: '#2563eb', weight: 3, dashArray: '6 4', interactive: false };

/**
 * Historical telemetry rows that should receive small history-point markers.
 * The latest row is excluded — the interactive fleet marker represents the
 * drone's current position and must not be covered by a non-interactive overlay.
 */
export function getHistoricalPoints(history: DroneTelemetry[]): DroneTelemetry[] {
  if (history.length <= 1) {
    return [];
  }
  return history.slice(0, -1);
}

/** Leaflet options for the selected drone's path polyline (non-interactive). */
export function getHistoryPolylineOptions(): PolylineOptions {
  return PATH_STYLE;
}

/** Leaflet options for one historical path point marker (non-interactive). */
export function getHistoryPointMarkerOptions(): CircleMarkerOptions {
  return { ...getHistoryPointStyle(), interactive: false };
}

/**
 * Status message shown above the map for the current selection once history
 * has loaded. Returns `null` while history is empty (including the brief
 * in-flight state before the HTTP response arrives).
 */
export function getSelectedHistoryMessage(droneId: string, historyLength: number): string | null {
  if (historyLength === 0) {
    return null;
  }
  if (historyLength === 1) {
    return `${droneId} has only one telemetry point — no path history available.`;
  }
  return `Showing path history for ${droneId} — click its marker again to clear.`;
}
