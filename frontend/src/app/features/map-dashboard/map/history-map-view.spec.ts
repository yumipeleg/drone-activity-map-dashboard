import { describe, expect, it } from 'vitest';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import { computeHistoryMapView, getHistoryFitBoundsOptions, HISTORY_FIT_MAX_ZOOM } from './history-map-view';

function point(lat: number, lng: number): DroneTelemetry {
  return {
    id: 1,
    drone_id: 'DRONE-001',
    drone_type: 'Quadcopter',
    operator_id: 'OP-123',
    latitude: lat,
    longitude: lng,
    altitude_m: 120,
    speed_kmh: 45,
    battery_percent: 76,
    timestamp: '2026-06-28T10:30:00Z',
    status: 'active',
    created_at: '2026-06-28T10:30:01Z',
  };
}

describe('computeHistoryMapView', () => {
  it('returns no view target for an empty history', () => {
    expect(computeHistoryMapView([])).toEqual({ bounds: null, center: null });
  });

  it('returns a center (not bounds) for a single history point', () => {
    expect(computeHistoryMapView([point(32.1, 34.2)])).toEqual({
      bounds: null,
      center: [32.1, 34.2],
    });
  });

  it('returns bounds for multiple history points', () => {
    const view = computeHistoryMapView([point(32.0, 34.0), point(32.5, 34.5)]);

    expect(view.center).toBeNull();
    expect(view.bounds).toEqual([
      [32.0, 34.0],
      [32.5, 34.5],
    ]);
  });
});

describe('getHistoryFitBoundsOptions', () => {
  it('uses asymmetric padding and a moderate max zoom for path overview', () => {
    expect(getHistoryFitBoundsOptions()).toEqual({
      maxZoom: HISTORY_FIT_MAX_ZOOM,
      paddingTopLeft: [40, 160],
      paddingBottomRight: [40, 40],
    });
    expect(HISTORY_FIT_MAX_ZOOM).toBe(13);
  });
});
