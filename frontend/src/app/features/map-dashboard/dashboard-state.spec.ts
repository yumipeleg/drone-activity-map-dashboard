import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { API_BASE_URL } from '../../core/api/api-config';
import { DronePage } from '../../core/models/drone-page';
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

const OTHER_DRONE: DroneTelemetry = {
  ...SAMPLE_DRONE,
  id: 2,
  drone_id: 'DRONE-002',
};

function page(items: DroneTelemetry[]): DronePage {
  return { items, total: items.length, page: 1, page_size: items.length };
}

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
    input_file: 'sample_drones.json',
    ...overrides,
  };
}

function queuedRun(overrides: Partial<PipelineRun> = {}): PipelineRun {
  return completedRun({
    status: 'queued',
    finished_at: null,
    total_records: 0,
    valid_records: 0,
    invalid_records: 0,
    duplicate_records: 0,
    error_message: null,
    ...overrides,
  });
}

describe('DashboardStateService', () => {
  let service: DashboardStateService;
  let httpMock: HttpTestingController;

  function expectPipelineRunsList() {
    return httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/pipeline/runs` && r.method === 'GET');
  }

  function expectPipelineInputs() {
    return httpMock.expectOne(`${API_BASE_URL}/api/pipeline/inputs`);
  }

  function flushAvailableInputFiles(files = ['sample_drones.json']) {
    service.loadAvailableInputFiles();
    expectPipelineInputs().flush({ files, default_file: 'sample_drones.json' });
  }

  function prepareRunPipeline() {
    flushAvailableInputFiles();
  }

  function expectGetRun(runId: number) {
    return httpMock.expectOne(`${API_BASE_URL}/api/pipeline/runs/${runId}`);
  }

  function expectRunPipelinePost() {
    const req = httpMock.expectOne(`${API_BASE_URL}/api/pipeline/run`);
    expect(req.request.body).toEqual({ input_file: 'sample_drones.json' });
    return req;
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(DashboardStateService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function expectDronesRequest() {
    return httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/drones` && r.method === 'GET');
  }

  it('loadInitial() fires GET /api/drones, GET /api/pipeline/runs, and GET /api/pipeline/inputs', () => {
    service.loadInitial();

    const dronesReq = expectDronesRequest();
    expect(dronesReq.request.params.get('latest_only')).toBe('true');
    dronesReq.flush(page([SAMPLE_DRONE]));

    httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/pipeline/runs`).flush([completedRun()]);
    expectPipelineInputs().flush({
      files: ['sample_drones.json'],
      default_file: 'sample_drones.json',
    });

    expect(service.drones()).toEqual([SAMPLE_DRONE]);
    expect(service.pipelineRuns()).toEqual([completedRun()]);
    expect(service.availableInputFiles()).toEqual(['sample_drones.json']);
    expect(service.selectedInputFile()).toBe('sample_drones.json');
    expect(service.canRunPipeline()).toBe(true);
    expect(service.dronesLoading()).toBe(false);
    expect(service.pipelineRunsLoading()).toBe(false);
    expect(service.inputFilesLoading()).toBe(false);
    httpMock.expectNone(`${API_BASE_URL}/api/stats`);
  });

  it('applyFilters() remembers the filters and re-fetches drones (latest_only=true) with them', () => {
    service.applyFilters({ droneType: 'Quadcopter' });

    const req = expectDronesRequest();
    expect(req.request.params.get('drone_type')).toBe('Quadcopter');
    expect(req.request.params.get('latest_only')).toBe('true');
    req.flush(page([]));

    expect(service.currentFilters()).toEqual({ droneType: 'Quadcopter' });
  });

  it('a drones request failure sets dronesError and clears loading', () => {
    service.refreshDrones();

    expectDronesRequest().flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });

    expect(service.dronesError()).toBe('boom');
    expect(service.dronesLoading()).toBe(false);
  });

  it('refreshDrones() clears the current selection when the selected drone disappears from the new results', () => {
    service.refreshDrones();
    expectDronesRequest().flush(page([SAMPLE_DRONE]));

    service.selectDrone('DRONE-001');
    httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`).flush([SAMPLE_DRONE]);
    expect(service.selectedDroneId()).toBe('DRONE-001');

    service.applyFilters({ droneType: 'Fixed Wing' });
    expectDronesRequest().flush(page([OTHER_DRONE]));

    expect(service.selectedDroneId()).toBeNull();
    expect(service.selectedDroneHistory()).toEqual([]);
  });

  it('refreshDrones() keeps the current selection/history when the selected drone is still present', () => {
    service.refreshDrones();
    expectDronesRequest().flush(page([SAMPLE_DRONE]));

    service.selectDrone('DRONE-001');
    httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`).flush([SAMPLE_DRONE]);

    service.applyFilters({});
    expectDronesRequest().flush(page([SAMPLE_DRONE, OTHER_DRONE]));

    expect(service.selectedDroneId()).toBe('DRONE-001');
    expect(service.selectedDroneHistory()).toEqual([SAMPLE_DRONE]);
  });

  it('selectDrone() fetches history and stores it', () => {
    service.selectDrone('DRONE-001');

    expect(service.selectedDroneId()).toBe('DRONE-001');
    expect(service.historyLoading()).toBe(true);

    httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`).flush([SAMPLE_DRONE]);

    expect(service.selectedDroneHistory()).toEqual([SAMPLE_DRONE]);
    expect(service.historyLoading()).toBe(false);
    expect(service.historyError()).toBeNull();
  });

  it('selectDrone() called again with the same drone_id deselects it and clears its history', () => {
    service.selectDrone('DRONE-001');
    httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`).flush([SAMPLE_DRONE]);

    service.selectDrone('DRONE-001');

    expect(service.selectedDroneId()).toBeNull();
    expect(service.selectedDroneHistory()).toEqual([]);
    httpMock.expectNone(`${API_BASE_URL}/api/drones/DRONE-001/history`);
  });

  it('selectDrone() with a different drone_id replaces the previous selection and path', () => {
    service.selectDrone('DRONE-001');
    httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`).flush([SAMPLE_DRONE]);

    service.selectDrone('DRONE-002');
    expect(service.selectedDroneId()).toBe('DRONE-002');
    expect(service.selectedDroneHistory()).toEqual([]);

    httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-002/history`).flush([OTHER_DRONE]);
    expect(service.selectedDroneHistory()).toEqual([OTHER_DRONE]);
  });

  it('a history request failure sets historyError and clears loading', () => {
    service.selectDrone('DRONE-001');

    httpMock
      .expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`)
      .flush({ detail: 'history down' }, { status: 500, statusText: 'Server Error' });

    expect(service.historyError()).toBe('history down');
    expect(service.historyLoading()).toBe(false);
  });

  it('clearSelection() deselects the drone and clears its history/error state', () => {
    service.selectDrone('DRONE-001');
    httpMock
      .expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`)
      .flush({ detail: 'boom' }, { status: 500, statusText: 'Server Error' });
    expect(service.historyError()).toBe('boom');

    service.clearSelection();

    expect(service.selectedDroneId()).toBeNull();
    expect(service.selectedDroneHistory()).toEqual([]);
    expect(service.historyError()).toBeNull();
    expect(service.historyLoading()).toBe(false);
  });

  it('a stale history response cannot overwrite a newer selection (race protection)', () => {
    service.selectDrone('DRONE-001');
    const requestA = httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`);

    service.selectDrone('DRONE-002');
    const requestB = httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-002/history`);

    requestB.flush([OTHER_DRONE]);
    expect(service.selectedDroneHistory()).toEqual([OTHER_DRONE]);

    requestA.flush([SAMPLE_DRONE]);

    expect(service.selectedDroneId()).toBe('DRONE-002');
    expect(service.selectedDroneHistory()).toEqual([OTHER_DRONE]);
  });

  it('a stale history response cannot resurrect history after a deselect (race protection)', () => {
    service.selectDrone('DRONE-001');
    const requestA = httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`);

    service.selectDrone('DRONE-001');
    expect(service.selectedDroneId()).toBeNull();

    requestA.flush([SAMPLE_DRONE]);

    expect(service.selectedDroneId()).toBeNull();
    expect(service.selectedDroneHistory()).toEqual([]);
  });

  it('loadAvailableInputFiles() picks default_file when present', () => {
    flushAvailableInputFiles(['custom.json', 'sample_drones.json']);

    expect(service.availableInputFiles()).toEqual(['custom.json', 'sample_drones.json']);
    expect(service.selectedInputFile()).toBe('sample_drones.json');
    expect(service.canRunPipeline()).toBe(true);
  });

  it('loadAvailableInputFiles() falls back to the first file when default is absent', () => {
    flushAvailableInputFiles(['alpha.json', 'beta.csv']);

    expect(service.selectedInputFile()).toBe('alpha.json');
  });

  it('canRunPipeline() is false while input files are loading', () => {
    service.loadAvailableInputFiles();
    expect(service.canRunPipeline()).toBe(false);
    expectPipelineInputs().flush({ files: ['sample_drones.json'], default_file: 'sample_drones.json' });
    expect(service.canRunPipeline()).toBe(true);
  });

  it('canRunPipeline() is false after input file loading fails', () => {
    service.loadAvailableInputFiles();
    expectPipelineInputs().flush({ detail: 'down' }, { status: 500, statusText: 'Server Error' });

    expect(service.inputFilesError()).toBe('down');
    expect(service.selectedInputFile()).toBeNull();
    expect(service.canRunPipeline()).toBe(false);
  });

  it('canRunPipeline() is false when the input file list is empty', () => {
    flushAvailableInputFiles([]);

    expect(service.canRunPipeline()).toBe(false);
  });

  it('runPipeline() forwards the selected filename', () => {
    vi.useFakeTimers();
    prepareRunPipeline();

    service.runPipeline();

    expectRunPipelinePost().flush(queuedRun({ id: 42 }));
    expectPipelineRunsList().flush([queuedRun({ id: 42 })]);

    vi.advanceTimersByTime(0);
    expectGetRun(42).flush(completedRun({ id: 42 }));

    expectDronesRequest().flush(page([SAMPLE_DRONE]));
    expectPipelineRunsList().flush([completedRun({ id: 42 })]);

    vi.useRealTimers();
  });

  it('runPipeline(): POST queued starts polling the returned run id', () => {
    vi.useFakeTimers();
    prepareRunPipeline();

    service.runPipeline();
    expect(service.pipelineRunning()).toBe(true);

    expectRunPipelinePost().flush(queuedRun({ id: 42 }));
    expectPipelineRunsList().flush([queuedRun({ id: 42 })]);

    vi.advanceTimersByTime(0);
    expectGetRun(42).flush(completedRun({ id: 42 }));

    expectDronesRequest().flush(page([SAMPLE_DRONE]));
    expectPipelineRunsList().flush([completedRun({ id: 42 })]);

    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBeNull();
    httpMock.expectNone(`${API_BASE_URL}/api/pipeline/runs/42`);

    vi.useRealTimers();
  });

  it('runPipeline(): queued → completed refreshes drones and pipeline history once at terminal status', () => {
    vi.useFakeTimers();
    prepareRunPipeline();

    service.applyFilters({ droneType: 'Quadcopter' });
    expectDronesRequest().flush(page([]));

    service.runPipeline();

    expectRunPipelinePost().flush(queuedRun({ id: 7 }));
    expectPipelineRunsList().flush([queuedRun({ id: 7 })]);

    vi.advanceTimersByTime(0);
    expectGetRun(7).flush(queuedRun({ id: 7 }));
    expect(service.pipelineRunning()).toBe(true);

    vi.advanceTimersByTime(1000);
    expectGetRun(7).flush(completedRun({ id: 7 }));

    const dronesReq = expectDronesRequest();
    expect(dronesReq.request.params.get('drone_type')).toBe('Quadcopter');
    expect(dronesReq.request.params.get('latest_only')).toBe('true');
    dronesReq.flush(page([SAMPLE_DRONE]));
    expectPipelineRunsList().flush([completedRun({ id: 7 })]);

    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBeNull();
    expect(service.drones()).toEqual([SAMPLE_DRONE]);
    httpMock.expectNone(`${API_BASE_URL}/api/pipeline/runs/7`);
    httpMock.expectNone(`${API_BASE_URL}/api/stats`);

    vi.useRealTimers();
  });

  it('runPipeline(): queued → started → completed polls until terminal status', () => {
    vi.useFakeTimers();
    prepareRunPipeline();

    service.runPipeline();

    expectRunPipelinePost().flush(queuedRun({ id: 9 }));
    expectPipelineRunsList().flush([queuedRun({ id: 9 })]);

    vi.advanceTimersByTime(0);
    expectGetRun(9).flush(queuedRun({ id: 9 }));

    vi.advanceTimersByTime(1000);
    expectGetRun(9).flush(
      completedRun({ id: 9, status: 'started', finished_at: null, total_records: 0, valid_records: 0 }),
    );

    vi.advanceTimersByTime(1000);
    expectGetRun(9).flush(completedRun({ id: 9 }));

    expectDronesRequest().flush(page([SAMPLE_DRONE]));
    expectPipelineRunsList().flush([completedRun({ id: 9 })]);

    expect(service.pipelineRunning()).toBe(false);
    httpMock.expectNone(`${API_BASE_URL}/api/pipeline/runs/9`);

    vi.useRealTimers();
  });

  it('runPipeline(): failed terminal result refreshes drones and pipeline history and sets pipelineError', () => {
    vi.useFakeTimers();
    prepareRunPipeline();

    const failedRun = completedRun({
      id: 3,
      status: 'failed',
      valid_records: 3,
      error_message: 'Input file not found',
    });

    service.runPipeline();

    expectRunPipelinePost().flush(queuedRun({ id: 3 }));
    expectPipelineRunsList().flush([queuedRun({ id: 3 })]);

    vi.advanceTimersByTime(0);
    expectGetRun(3).flush(failedRun);

    expectDronesRequest().flush(page([SAMPLE_DRONE]));
    expectPipelineRunsList().flush([failedRun]);

    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBe('Input file not found');
    expect(service.drones()).toEqual([SAMPLE_DRONE]);
    expect(service.pipelineRuns()).toEqual([failedRun]);
    httpMock.expectNone(`${API_BASE_URL}/api/stats`);

    vi.useRealTimers();
  });

  it('runPipeline(): HTTP 503 on POST does not start polling and exposes backend error_message', () => {
    prepareRunPipeline();

    const enqueueFailed = completedRun({
      id: 11,
      status: 'failed',
      error_message: 'Failed to enqueue pipeline run: Connection refused',
    });

    service.runPipeline();

    httpMock
      .expectOne(`${API_BASE_URL}/api/pipeline/run`)
      .flush(enqueueFailed, { status: 503, statusText: 'Service Unavailable' });

    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBe('Failed to enqueue pipeline run: Connection refused');
    httpMock.expectNone(`${API_BASE_URL}/api/pipeline/runs/11`);
    httpMock.expectNone(`${API_BASE_URL}/api/drones`);
  });

  it('runPipeline(): does not start a second POST while pipelineRunning is true', () => {
    vi.useFakeTimers();
    prepareRunPipeline();

    service.runPipeline();

    const postReq = expectRunPipelinePost();
    service.runPipeline();

    httpMock.expectNone(`${API_BASE_URL}/api/pipeline/run`);

    postReq.flush(queuedRun({ id: 1 }));
    expectPipelineRunsList().flush([queuedRun({ id: 1 })]);
    vi.advanceTimersByTime(0);
    expectGetRun(1).flush(completedRun({ id: 1 }));
    expectDronesRequest().flush(page([]));
    expectPipelineRunsList().flush([completedRun({ id: 1 })]);

    vi.useRealTimers();
  });

  it('runPipeline(): on an HTTP-level POST failure, sets pipelineError and does not refresh anything', () => {
    prepareRunPipeline();

    service.runPipeline();

    httpMock
      .expectOne(`${API_BASE_URL}/api/pipeline/run`)
      .flush({ detail: 'Internal Server Error' }, { status: 500, statusText: 'Server Error' });

    expect(service.pipelineRunning()).toBe(false);
    expect(service.pipelineError()).toBe('Internal Server Error');
    httpMock.expectNone(`${API_BASE_URL}/api/pipeline/runs`);
    httpMock.expectNone(`${API_BASE_URL}/api/drones`);
    httpMock.expectNone(`${API_BASE_URL}/api/stats`);
  });
});
