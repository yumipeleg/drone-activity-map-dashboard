import { describe, expect, it } from 'vitest';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import { buildDronePopupHtml, escapeHtml } from './drone-popup';

const SAMPLE: DroneTelemetry = {
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
};

describe('escapeHtml', () => {
  it('escapes HTML-significant characters', () => {
    expect(escapeHtml('<script>&"\'')).toBe('&lt;script&gt;&amp;&quot;&#39;');
  });
});

describe('buildDronePopupHtml', () => {
  it('includes all 8 required fields', () => {
    const html = buildDronePopupHtml(SAMPLE);

    expect(html).toContain('DRONE-001');
    expect(html).toContain('Quadcopter');
    expect(html).toContain('OP-123');
    expect(html).toContain('120 m');
    expect(html).toContain('45 km/h');
    expect(html).toContain('76%');
    expect(html).toContain('active');
    expect(html).toContain(new Date(SAMPLE.timestamp).toLocaleString());
  });

  it('HTML-escapes a drone_id containing unsafe characters', () => {
    const html = buildDronePopupHtml({ ...SAMPLE, drone_id: '<img src=x onerror=alert(1)>' });

    expect(html).not.toContain('<img src=x');
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
  });
});
