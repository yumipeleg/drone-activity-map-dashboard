import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { DroneFilters } from '../models/drone-filters';
import { DronePage } from '../models/drone-page';
import { DroneTelemetry } from '../models/drone-telemetry';
import { API_BASE_URL } from './api-config';
import { buildDroneQueryParams } from './query-params';

/**
 * Thin HTTP wrapper for the drone telemetry endpoints — no business logic
 * here, mirroring the backend's own route -> service split
 * (backend/app/api/routes/drones.py, backend/app/services/drones.py).
 */
@Injectable({ providedIn: 'root' })
export class DronesApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/api/drones`;

  /**
   * GET /api/drones?latest_only=true (+ the given filters) — one row per
   * drone, its own current/latest telemetry event. This is the only
   * listing mode the dashboard's map uses: `latest_only` is fixed here
   * (not exposed as a caller-provided option), so it's never accidentally
   * left off. There is currently no dashboard view that needs the raw,
   * un-collapsed historical listing, so a separate general-purpose
   * `list()` method isn't added until one exists.
   */
  listLatest(filters: DroneFilters): Observable<DronePage> {
    const params = buildDroneQueryParams(filters).set('latest_only', 'true');
    return this.http.get<DronePage>(this.baseUrl, { params });
  }

  /**
   * GET /api/drones/{drone_id}/history — full recorded path for one
   * business drone ID, oldest to newest, independent of dashboard
   * filters. `drone_id` is URL-encoded defensively even though the
   * exercise's own IDs (e.g. "DRONE-001") never require it.
   */
  getHistory(droneId: string): Observable<DroneTelemetry[]> {
    return this.http.get<DroneTelemetry[]>(`${this.baseUrl}/${encodeURIComponent(droneId)}/history`);
  }

  /** GET /api/drones/{telemetry_id} — internal telemetry row primary key, not the business drone_id. */
  get(id: number): Observable<DroneTelemetry> {
    return this.http.get<DroneTelemetry>(`${this.baseUrl}/${id}`);
  }
}
