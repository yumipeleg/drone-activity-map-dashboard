import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { DroneFilters } from '../models/drone-filters';
import { DroneTelemetry } from '../models/drone-telemetry';
import { API_BASE_URL } from './api-config';
import { buildDroneQueryParams } from './query-params';

/**
 * Thin HTTP wrapper for `GET /api/drones` and `GET /api/drones/{id}` — no
 * business logic here, mirroring the backend's own route -> service split
 * (backend/app/api/routes/drones.py, backend/app/services/drones.py).
 */
@Injectable({ providedIn: 'root' })
export class DronesApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/api/drones`;

  list(filters: DroneFilters): Observable<DroneTelemetry[]> {
    return this.http.get<DroneTelemetry[]>(this.baseUrl, { params: buildDroneQueryParams(filters) });
  }

  get(id: number): Observable<DroneTelemetry> {
    return this.http.get<DroneTelemetry>(`${this.baseUrl}/${id}`);
  }
}
