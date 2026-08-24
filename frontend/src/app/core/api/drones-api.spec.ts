import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { DronePage } from '../models/drone-page';
import { DroneTelemetry } from '../models/drone-telemetry';
import { API_BASE_URL } from './api-config';
import { DronesApiService } from './drones-api';

describe('DronesApiService', () => {
  let service: DronesApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(DronesApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('listLatest() requests GET /api/drones with latest_only=true and the built filter params', () => {
    const page: DronePage = { items: [], total: 0, page: 1, page_size: 0 };

    service.listLatest({ droneType: 'Quadcopter', minBattery: 50 }).subscribe((result) => {
      expect(result).toBe(page);
    });

    const req = httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/drones` && r.method === 'GET');
    expect(req.request.params.get('latest_only')).toBe('true');
    expect(req.request.params.get('drone_type')).toBe('Quadcopter');
    expect(req.request.params.get('min_battery')).toBe('50');
    req.flush(page);
  });

  it('listLatest() always sends latest_only=true even when no filters are provided', () => {
    service.listLatest({}).subscribe();

    const req = httpMock.expectOne((r) => r.url === `${API_BASE_URL}/api/drones`);
    expect(req.request.params.get('latest_only')).toBe('true');
    expect(req.request.params.keys().length).toBe(1);
    req.flush({ items: [], total: 0, page: 1, page_size: 0 });
  });

  it('getHistory() requests GET /api/drones/{droneId}/history', () => {
    const history: DroneTelemetry[] = [];

    service.getHistory('DRONE-001').subscribe((result) => {
      expect(result).toBe(history);
    });

    const req = httpMock.expectOne(`${API_BASE_URL}/api/drones/DRONE-001/history`);
    expect(req.request.method).toBe('GET');
    req.flush(history);
  });

  it('getHistory() URL-encodes the drone_id path segment', () => {
    service.getHistory('DRONE/001 A').subscribe();

    const req = httpMock.expectOne(`${API_BASE_URL}/api/drones/${encodeURIComponent('DRONE/001 A')}/history`);
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('get() requests GET /api/drones/{id}', () => {
    service.get(5).subscribe();

    const req = httpMock.expectOne(`${API_BASE_URL}/api/drones/5`);
    expect(req.request.method).toBe('GET');
    req.flush({});
  });
});
