import { describe, expect, it } from 'vitest';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import { getMarkerStyle, getMarkerLegendEntries } from './marker-style';

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

describe('getMarkerStyle', () => {
  it('returns the normal style for an active drone with healthy battery', () => {
    const style = getMarkerStyle(drone({ status: 'active', battery_percent: 76 }));

    expect(style.dashArray).toBeUndefined();
    expect(style).toEqual({ radius: 8, color: '#1d7a45', fillColor: '#32a05f', fillOpacity: 0.85 });
  });

  it('treats battery_percent 19 as low battery', () => {
    const style = getMarkerStyle(drone({ status: 'active', battery_percent: 19 }));

    expect(style).toEqual({ radius: 8, color: '#b54708', fillColor: '#fdb022', fillOpacity: 0.9 });
  });

  it('treats battery_percent 20 as NOT low battery', () => {
    const style = getMarkerStyle(drone({ status: 'active', battery_percent: 20 }));

    expect(style).toEqual({ radius: 8, color: '#1d7a45', fillColor: '#32a05f', fillOpacity: 0.85 });
  });

  it('returns the lost-signal style (dashed outline) for a lost_signal drone with healthy battery', () => {
    const style = getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 80 }));

    expect(style).toEqual({ radius: 8, color: '#b42318', fillColor: '#f97066', fillOpacity: 0.85, dashArray: '4' });
  });

  it('returns the combined low-battery + lost-signal style when both conditions hold', () => {
    const style = getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 5 }));

    expect(style).toEqual({ radius: 8, color: '#7a271a', fillColor: '#7a271a', fillOpacity: 0.9, dashArray: '4' });
  });

  it('uses the same radius for every marker state', () => {
    const normal = getMarkerStyle(drone({ status: 'active', battery_percent: 80 }));
    const lowBattery = getMarkerStyle(drone({ status: 'active', battery_percent: 5 }));
    const lostSignal = getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 80 }));
    const both = getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 5 }));

    expect(new Set([normal.radius, lowBattery.radius, lostSignal.radius, both.radius]).size).toBe(1);
    expect(normal.radius).toBe(8);
  });

  it('only lost-signal states use a dashed outline', () => {
    expect(getMarkerStyle(drone({ status: 'active', battery_percent: 80 })).dashArray).toBeUndefined();
    expect(getMarkerStyle(drone({ status: 'active', battery_percent: 5 })).dashArray).toBeUndefined();
    expect(getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 80 })).dashArray).toBe('4');
    expect(getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 5 })).dashArray).toBe('4');
  });
});

describe('getMarkerLegendEntries', () => {
  it('returns one entry per marker state, each styled via getMarkerStyle', () => {
    const entries = getMarkerLegendEntries();

    expect(entries.map((entry) => entry.label)).toEqual([
      'Normal',
      'Low battery (<20%)',
      'Lost signal',
      'Low battery + lost signal',
    ]);
    expect(entries[0].style).toEqual(getMarkerStyle(drone({ status: 'active', battery_percent: 76 })));
    expect(entries[1].style).toEqual(getMarkerStyle(drone({ status: 'active', battery_percent: 19 })));
    expect(entries[2].style).toEqual(getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 80 })));
    expect(entries[3].style).toEqual(getMarkerStyle(drone({ status: 'lost_signal', battery_percent: 5 })));
  });
});
