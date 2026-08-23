import { describe, expect, it } from 'vitest';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import { computeBounds } from './map-bounds';

function drone(latitude: number, longitude: number): DroneTelemetry {
  return {
    id: 1,
    drone_id: 'DRONE-001',
    drone_type: 'Quadcopter',
    operator_id: 'OP-123',
    latitude,
    longitude,
    altitude_m: 100,
    speed_kmh: 10,
    battery_percent: 50,
    timestamp: '2026-06-28T10:30:00Z',
    status: 'active',
    created_at: '2026-06-28T10:30:01Z',
  };
}

describe('computeBounds', () => {
  it('returns null for an empty list', () => {
    expect(computeBounds([])).toBeNull();
  });

  it('returns a [lat, lng] pair per drone, covering every point', () => {
    const bounds = computeBounds([drone(32.08, 34.78), drone(31.77, 35.21)]);

    expect(bounds).toEqual([
      [32.08, 34.78],
      [31.77, 35.21],
    ]);
  });
});
