import { LatLngBoundsExpression } from 'leaflet';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';

/** Close enough to see a lone history point without street-level over-zoom. */
export const SINGLE_HISTORY_POINT_ZOOM = 13;

/** Max zoom when framing a multi-point history path. */
export const HISTORY_FIT_MAX_ZOOM = 13;

export interface HistoryFitBoundsOptions {
  maxZoom: number;
  paddingTopLeft: [number, number];
  paddingBottomRight: [number, number];
}

/**
 * Asymmetric fitBounds padding for multi-point histories. Extra top padding
 * (via paddingTopLeft's y component) reserves space so the selected marker's
 * popup does not obscure the path after framing.
 */
export function getHistoryFitBoundsOptions(): HistoryFitBoundsOptions {
  return {
    maxZoom: HISTORY_FIT_MAX_ZOOM,
    paddingTopLeft: [40, 160],
    paddingBottomRight: [40, 40],
  };
}

export interface HistoryMapView {
  /** Multi-point histories: passed to `fitBounds`. */
  bounds: LatLngBoundsExpression | null;
  /** Single-point histories: passed to `setView` (a bounds fit would over-zoom). */
  center: [number, number] | null;
}

/**
 * Pure helper deciding how the map should frame a selected drone's history.
 * Returns `{ bounds: null, center: null }` for an empty history.
 */
export function computeHistoryMapView(history: DroneTelemetry[]): HistoryMapView {
  if (history.length === 0) {
    return { bounds: null, center: null };
  }
  if (history.length === 1) {
    return { bounds: null, center: [history[0].latitude, history[0].longitude] };
  }
  return {
    bounds: history.map((record) => [record.latitude, record.longitude]),
    center: null,
  };
}
