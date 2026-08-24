import { DroneTelemetry } from '../../../core/models/drone-telemetry';

/** Options accepted by `L.circleMarker(latlng, options)`. Kept as a plain object (no Leaflet import) so this stays a pure, easily unit-testable function. */
export interface MarkerStyle {
  radius: number;
  color: string;
  fillColor: string;
  fillOpacity: number;
  dashArray?: string;
}

export interface MarkerLegendEntry {
  label: string;
  style: MarkerStyle;
}

/** Battery strictly below this percentage counts as "low battery" — 19 is low, 20 is not. */
const LOW_BATTERY_THRESHOLD = 20;

/** Shared CircleMarker radius for every fleet-marker state. */
const FLEET_MARKER_RADIUS = 8;

/**
 * Visual style for one drone's marker. Four clearly distinguishable
 * states using color, fill, and a dashed outline for lost signal:
 *
 * - normal: solid green circle
 * - low battery only: solid amber circle
 * - lost signal only: red circle with a dashed outline
 * - low battery + lost signal: dark-red circle with a dashed outline
 *
 * Pure function — no Leaflet dependency — so it's testable without
 * mounting a map (see marker-style.spec.ts).
 */
export function getMarkerStyle(drone: DroneTelemetry): MarkerStyle {
  const isLowBattery = drone.battery_percent < LOW_BATTERY_THRESHOLD;
  const isLostSignal = drone.status === 'lost_signal';

  if (isLowBattery && isLostSignal) {
    return { radius: FLEET_MARKER_RADIUS, color: '#7a271a', fillColor: '#7a271a', fillOpacity: 0.9, dashArray: '4' };
  }
  if (isLostSignal) {
    return { radius: FLEET_MARKER_RADIUS, color: '#b42318', fillColor: '#f97066', fillOpacity: 0.85, dashArray: '4' };
  }
  if (isLowBattery) {
    return { radius: FLEET_MARKER_RADIUS, color: '#b54708', fillColor: '#fdb022', fillOpacity: 0.9 };
  }
  return { radius: FLEET_MARKER_RADIUS, color: '#1d7a45', fillColor: '#32a05f', fillOpacity: 0.85 };
}

/** Minimal telemetry stub — only `battery_percent` and `status` affect marker styling. */
function legendDrone(battery_percent: number, status: DroneTelemetry['status']): DroneTelemetry {
  return {
    id: 0,
    drone_id: 'LEGEND',
    drone_type: '',
    operator_id: '',
    latitude: 0,
    longitude: 0,
    altitude_m: 0,
    speed_kmh: 0,
    battery_percent,
    timestamp: '',
    status,
    created_at: '',
  };
}

/** Legend rows for the four fleet-marker states, each styled via `getMarkerStyle()`. */
export function getMarkerLegendEntries(): MarkerLegendEntry[] {
  return [
    { label: 'Normal', style: getMarkerStyle(legendDrone(76, 'active')) },
    { label: 'Low battery (<20%)', style: getMarkerStyle(legendDrone(19, 'active')) },
    { label: 'Lost signal', style: getMarkerStyle(legendDrone(80, 'lost_signal')) },
    { label: 'Low battery + lost signal', style: getMarkerStyle(legendDrone(5, 'lost_signal')) },
  ];
}

function hexToRgba(hex: string, alpha: number): string {
  const normalized = hex.replace('#', '');
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Inline CSS for a legend swatch that mirrors one `MarkerStyle` CircleMarker. */
export function markerStyleToSwatchCss(style: MarkerStyle): Record<string, string> {
  const diameter = style.radius * 2;
  return {
    width: `${diameter}px`,
    height: `${diameter}px`,
    'background-color': hexToRgba(style.fillColor, style.fillOpacity),
    'border-color': style.color,
    'border-width': '2px',
    'border-style': style.dashArray ? 'dashed' : 'solid',
    'border-radius': '50%',
    'box-sizing': 'border-box',
    'flex-shrink': '0',
  };
}
