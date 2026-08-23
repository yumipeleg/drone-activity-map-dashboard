import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { PipelineRun } from '../models/pipeline-run';
import { API_BASE_URL } from './api-config';

/**
 * Thin HTTP wrapper for the pipeline endpoints — no business logic here,
 * mirroring backend/app/api/routes/pipeline.py.
 */
@Injectable({ providedIn: 'root' })
export class PipelineApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/api/pipeline`;

  /** POST /api/pipeline/run — always resolves with the full run, even for a domain-level "failed" status (see DashboardStateService.runPipeline). */
  runPipeline(): Observable<PipelineRun> {
    return this.http.post<PipelineRun>(`${this.baseUrl}/run`, {});
  }

  listRuns(limit = 20): Observable<PipelineRun[]> {
    const params = new HttpParams().set('limit', limit);
    return this.http.get<PipelineRun[]>(`${this.baseUrl}/runs`, { params });
  }

  getRun(id: number): Observable<PipelineRun> {
    return this.http.get<PipelineRun>(`${this.baseUrl}/runs/${id}`);
  }
}
