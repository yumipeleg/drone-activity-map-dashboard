import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { API_BASE_URL } from './api-config';
import { PipelineApiService } from './pipeline-api';

describe('PipelineApiService', () => {
  let service: PipelineApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(PipelineApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('runPipeline() POSTs to /api/pipeline/run', () => {
    service.runPipeline().subscribe();

    const req = httpMock.expectOne(`${API_BASE_URL}/api/pipeline/run`);
    expect(req.request.method).toBe('POST');
    req.flush({ id: 1, status: 'completed' });
  });

  it('listRuns() requests GET /api/pipeline/runs with a limit param', () => {
    service.listRuns(10).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === `${API_BASE_URL}/api/pipeline/runs` && r.method === 'GET',
    );
    expect(req.request.params.get('limit')).toBe('10');
    req.flush([]);
  });

  it('listRuns() defaults to limit=100 when called with no argument', () => {
    service.listRuns().subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === `${API_BASE_URL}/api/pipeline/runs` && r.method === 'GET',
    );
    expect(req.request.params.get('limit')).toBe('100');
    req.flush([]);
  });

  it('getRun() requests GET /api/pipeline/runs/{id}', () => {
    service.getRun(7).subscribe();

    const req = httpMock.expectOne(`${API_BASE_URL}/api/pipeline/runs/7`);
    expect(req.request.method).toBe('GET');
    req.flush({});
  });
});
