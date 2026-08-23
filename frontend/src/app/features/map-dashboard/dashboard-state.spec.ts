import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-config';
import { DroneTelemetry } from '../../core/models/drone-telemetry';
import { PipelineRun } from '../../core/models/pipeline-run';
import { DashboardStateService } from './dashboard-state';

const SAMPLE_DRONE: DroneTelemetry = {
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

function completedRun(overrides: Partial<PipelineRun> = {}): PipelineRun {
  return {
    id: 1,
    started_at: '2026-06-28T10:00:00Z',
    finished_at: '2026-06-28T10:00:01Z',
    status: 'completed',
    total_records: 8,
    valid_records: 7,
    invalid_records: 1,
    duplicate_records: 0,
    error_message: null,
    ...overrides,
  };
}

describe('DashboardStateService', () => {
  let service: DashboardStateService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(DashboardStateService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loadInitial() fires both GET /api/drones and GET /api/pipeline/runs', () => {
    service.loadInitial();

    httpMock.expectOne(`${API_BASE_URL}/api/drones`).flush([SAMPLE_DRONE]);
    httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/pipeline/runs`).flush([completedRun()]);

    expect(service.drones()).toEqual([SAMPLE_DRONE]);
    expect(service.pipelineRuns()).toEqual([completedRun()]);
    expect(service.dronesLoading()).toBe(false);
    expect(service.pipelineRunsLoading()).toBe(false);
  });

  it('applyFilters() remembers the filters and re-fetches drones with them', () => {
    service.applyFilters({ droneType: 'Quadcopter' });

    const req = httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/drones`);
    expect(req.request.params.get('drone_type')).toBe('Quadcopter');
    req.flush([]);

    expect(service.currentFilters()).toEqual({ droneType: 'Quadcopter' });
  });

  it('a drones request failure sets dronesError and clears loading', () => {
    service.refreshDrones();

    httpMock.expectOne(`${API_BASE_URL}/api/drones`).flush(
      { detail: 'boom' },
      { status: 500, statusText: 'Server Error' },
    );

    expect(service.dronesError()).toBe('boom');
    expect(service.dronesLoading()).toBe(false);
  });

  it('runPipeline(): on domain "completed", refreshes drones (with current filters) and pipeline runs, clears any previous error', () => {
    service.applyFilters({ droneType: 'Quadcopter' });
    httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/drones`).flush([]);

    service.runPipeline();
    expect(service.pipelineRunning()).toBe(true);

    httpMock.expectOne(`${API_BASE_URL}/api/pipeline/run`).flush(completedRun());
    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBeNull();

    httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/pipeline/runs`).flush([completedRun()]);
    const dronesReq = httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/drones`);
    expect(dronesReq.request.params.get('drone_type')).toBe('Quadcopter');
    dronesReq.flush([SAMPLE_DRONE]);

    expect(service.drones()).toEqual([SAMPLE_DRONE]);
  });

  it('runPipeline(): on domain "failed", exposes error_message and still refreshes BOTH drones and pipeline runs', () => {
    // The backend commits valid telemetry rows individually, so a failed
    // run may still have persisted some rows before the failure — drones
    // must be refreshed even though the run's domain status is "failed".
    const failedRun = completedRun({ status: 'failed', valid_records: 3, error_message: 'Input file not found' });

    service.runPipeline();

    httpMock.expectOne(`${API_BASE_URL}/api/pipeline/run`).flush(failedRun);

    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBe('Input file not found');

    httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/drones`).flush([SAMPLE_DRONE]);
    httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/pipeline/runs`).flush([failedRun]);

    expect(service.drones()).toEqual([SAMPLE_DRONE]);
    expect(service.pipelineRuns()).toEqual([failedRun]);
  });

  it('runPipeline(): on an HTTP-level failure, sets pipelineError and does not refresh anything', () => {
    service.runPipeline();

    httpMock
      .expectOne(`${API_BASE_URL}/api/pipeline/run`)
      .flush({ detail: 'Internal Server Error' }, { status: 500, statusText: 'Server Error' });

    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBe('Internal Server Error');
    httpMock.expectNone(`${API_BASE_URL}/api/pipeline/runs`);
    httpMock.expectNone(`${API_BASE_URL}/api/drones`);
  });
});
