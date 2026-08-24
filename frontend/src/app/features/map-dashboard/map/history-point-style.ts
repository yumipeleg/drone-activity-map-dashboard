/** Options for small history-path point markers — distinct from fleet markers. */
export interface HistoryPointStyle {
  radius: number;
  color: string;
  fillColor: string;
  fillOpacity: number;
}

/**
 * Small, unobtrusive CircleMarker style for each historical telemetry point
 * on the selected drone's path. Kept separate from `getMarkerStyle()` so
 * history points never compete visually with the current-fleet markers.
 */
export function getHistoryPointStyle(): HistoryPointStyle {
  return { radius: 4, color: '#1d4ed8', fillColor: '#93c5fd', fillOpacity: 0.9 };
}
