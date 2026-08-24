import { describe, expect, it } from 'vitest';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import {
  getHistoricalPoints,
  getHistoryPointMarkerOptions,
  getHistoryPolylineOptions,
  getSelectedHistoryMessage,
} from './history-render';

function point(id: number, lat = 32.0, lng = 34.0): DroneTelemetry {
  return {
    id,
    drone_id: 'DRONE-001',
    drone_type: 'Quadcopter',
    operator_id: 'OP-123',
    latitude: lat,
    longitude: lng,
    altitude_m: 120,
    speed_kmh: 45,
    battery_percent: 76,
    timestamp: `2026-06-28T10:${String(id).padStart(2, '0')}:00Z`,
    status: 'active',
    created_at: '2026-06-28T10:30:01Z',
  };
}

describe('getHistoricalPoints', () => {
  it('returns no historical points for an empty history', () => {
    expect(getHistoricalPoints([])).toEqual([]);
  });

  it('returns no historical points for a single-point history', () => {
    expect(getHistoricalPoints([point(1)])).toEqual([]);
  });

  it('returns every row except the latest for multi-point histories', () => {
    const history = [point(1), point(2), point(3)];
    expect(getHistoricalPoints(history)).toEqual([point(1), point(2)]);
  });
});

describe('history overlay options', () => {
  it('marks the polyline as non-interactive', () => {
    expect(getHistoryPolylineOptions().interactive).toBe(false);
  });

  it('marks history point markers as non-interactive', () => {
    expect(getHistoryPointMarkerOptions().interactive).toBe(false);
  });
});

describe('getSelectedHistoryMessage', () => {
  it('returns null for an empty history', () => {
    expect(getSelectedHistoryMessage('DRONE-003', 0)).toBeNull();
  });

  it('returns the single-point message when only one telemetry row exists', () => {
    expect(getSelectedHistoryMessage('DRONE-003', 1)).toBe(
      'DRONE-003 has only one telemetry point — no path history available.',
    );
  });

  it('returns the normal path-history message for two or more points', () => {
    expect(getSelectedHistoryMessage('DRONE-001', 3)).toBe(
      'Showing path history for DRONE-001 — click its marker again to clear.',
    );
  });
});
