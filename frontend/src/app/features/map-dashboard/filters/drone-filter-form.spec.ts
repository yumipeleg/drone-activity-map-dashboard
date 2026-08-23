import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardStateService } from '../dashboard-state';
import { DroneFilterForm } from './drone-filter-form';

describe('DroneFilterForm', () => {
  let applyFilters: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    applyFilters = vi.fn();
    TestBed.configureTestingModule({
      imports: [DroneFilterForm],
      providers: [{ provide: DashboardStateService, useValue: { applyFilters } }],
    });
  });

  it('submitting with a mix of filled/empty fields calls applyFilters with only the filled ones', () => {
    const fixture = TestBed.createComponent(DroneFilterForm);
    const component = fixture.componentInstance;

    component['form'].setValue({
      droneType: 'Quadcopter',
      status: null,
      operatorId: null,
      minBattery: 50,
      from: null,
      to: null,
    });
    component['applyFilters']();

    expect(applyFilters).toHaveBeenCalledWith({
      droneType: 'Quadcopter',
      status: undefined,
      operatorId: undefined,
      minBattery: 50,
      from: undefined,
      to: undefined,
    });
  });

  it('clearFilters resets the form and applies an empty filter set', () => {
    const fixture = TestBed.createComponent(DroneFilterForm);
    const component = fixture.componentInstance;

    component['form'].setValue({
      droneType: 'Quadcopter',
      status: 'active',
      operatorId: 'OP-123',
      minBattery: 50,
      from: '2026-06-01',
      to: '2026-06-28',
    });

    component['clearFilters']();

    expect(component['form'].value.droneType).toBeNull();
    expect(applyFilters).toHaveBeenCalledWith({});
  });
});
