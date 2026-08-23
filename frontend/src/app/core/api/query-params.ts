import { HttpParams } from '@angular/common/http';
import { DroneFilters } from '../models/drone-filters';

/**
 * Builds the query params for `GET /api/drones` from a `DroneFilters`
 * object, omitting any field that's `null`/`undefined`/an empty string —
 * the backend treats a missing parameter as "no filter", so an empty one
 * must never be sent (e.g. `?drone_type=`).
 */
export function buildDroneQueryParams(filters: DroneFilters): HttpParams {
  let params = new HttpParams();

  if (filters.droneType) {
    params = params.set('drone_type', filters.droneType);
  }
  if (filters.status) {
    params = params.set('status', filters.status);
  }
  if (filters.operatorId) {
    params = params.set('operator_id', filters.operatorId);
  }
  if (filters.minBattery != null) {
    params = params.set('min_battery', filters.minBattery);
  }
  if (filters.from) {
    params = params.set('from', filters.from);
  }
  if (filters.to) {
    params = params.set('to', filters.to);
  }

  return params;
}
