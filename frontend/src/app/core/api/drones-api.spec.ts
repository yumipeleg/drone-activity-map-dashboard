import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
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

  it('list() requests GET /api/drones with the built query params', () => {
    const sample: DroneTelemetry[] = [];

    service.list({ droneType: 'Quadcopter', minBattery: 50 }).subscribe((result) => {
      expect(result).toBe(sample);
    });

    const req = httpMock.expectOne(
      (r) => r.url === `${API_BASE_URL}/api/drones` && r.method === 'GET',
    );
    expect(req.request.params.get('drone_type')).toBe('Quadcopter');
    expect(req.request.params.get('min_battery')).toBe('50');
    req.flush(sample);
  });

  it('list() sends no query params when no filters are provided', () => {
    service.list({}).subscribe();

    const req = httpMock.expectOne(`${API_BASE_URL}/api/drones`);
    expect(req.request.params.keys().length).toBe(0);
    req.flush([]);
  });

  it('get() requests GET /api/drones/{id}', () => {
    service.get(5).subscribe();

    const req = httpMock.expectOne(`${API_BASE_URL}/api/drones/5`);
    expect(req.request.method).toBe('GET');
    req.flush({});
  });
});
