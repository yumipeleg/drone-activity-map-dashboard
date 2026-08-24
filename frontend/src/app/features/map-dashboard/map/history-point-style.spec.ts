import { describe, expect, it } from 'vitest';
import { getHistoryPointStyle } from './history-point-style';
import { getMarkerStyle } from './marker-style';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';

function drone(overrides: Partial<DroneTelemetry> = {}): DroneTelemetry {
  return {
    id: 1,
    drone_id: 'DRONE-001',
    drone_type: 'Quadcopter',
    operator_id: 'OP-123',
    latitude: 32.0853,
    longitude: 34.7818,
    altitude_m: 120,
    speed_kmh: 45,
    battery_percent: 76,
    timestamp: '2026-06-28T10:30:00Z',
    status: 'active',
    created_at: '2026-06-28T10:30:01Z',
    ...overrides,
  };
}

describe('getHistoryPointStyle', () => {
  it('returns a small style distinct from fleet marker styles', () => {
    const historyStyle = getHistoryPointStyle();
    const fleetStyle = getMarkerStyle(drone());

    expect(historyStyle.radius).toBeLessThan(fleetStyle.radius);
    expect(historyStyle.color).not.toBe(fleetStyle.color);
    expect(historyStyle.fillColor).not.toBe(fleetStyle.fillColor);
  });
});
