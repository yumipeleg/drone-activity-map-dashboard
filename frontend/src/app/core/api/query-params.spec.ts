import { describe, expect, it } from 'vitest';
import { buildDroneQueryParams } from './query-params';

describe('buildDroneQueryParams', () => {
  it('omits every param when no filters are set', () => {
    const params = buildDroneQueryParams({});
    expect(params.keys()).toEqual([]);
  });

  it('includes every provided filter under the backend snake_case name', () => {
    const params = buildDroneQueryParams({
      droneType: 'Quadcopter',
      status: 'lost_signal',
      operatorId: 'OP-123',
      minBattery: 50,
      from: '2026-06-01',
      to: '2026-06-28',
    });

    expect(params.get('drone_type')).toBe('Quadcopter');
    expect(params.get('status')).toBe('lost_signal');
    expect(params.get('operator_id')).toBe('OP-123');
    expect(params.get('min_battery')).toBe('50');
    expect(params.get('from')).toBe('2026-06-01');
    expect(params.get('to')).toBe('2026-06-28');
  });

  it('omits empty-string and undefined fields rather than sending them blank', () => {
    const params = buildDroneQueryParams({ droneType: '', operatorId: undefined });
    expect(params.has('drone_type')).toBe(false);
    expect(params.has('operator_id')).toBe(false);
  });

  it('includes minBattery of 0 (a falsy-but-valid value)', () => {
    const params = buildDroneQueryParams({ minBattery: 0 });
    expect(params.get('min_battery')).toBe('0');
  });
});
