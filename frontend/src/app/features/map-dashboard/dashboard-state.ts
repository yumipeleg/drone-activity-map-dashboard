import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { extractErrorMessage } from '../../core/api/http-error';
import { DronesApiService } from '../../core/api/drones-api';
import { PipelineApiService } from '../../core/api/pipeline-api';
import { DroneFilters } from '../../core/models/drone-filters';
import { DroneTelemetry } from '../../core/models/drone-telemetry';
import { PipelineRun } from '../../core/models/pipeline-run';

/**
 * Owns the dashboard's shared state and all orchestration between the two
 * API services and the dashboard components (route -> service -> SQLAlchemy
 * on the backend; here, component -> this service -> API service). No NgRx:
 * plain signals, matching AGENTS.md.
 *
 * Leaflet rendering objects (L.Map/L.LayerGroup/L.Polyline) never live here —
 * they stay local to DroneMap, which reads `selectedDroneHistory` via its
 * own `effect()`.
 */
@Injectable({ providedIn: 'root' })
export class DashboardStateService {
  private readonly dronesApi = inject(DronesApiService);
  private readonly pipelineApi = inject(PipelineApiService);

  private readonly _drones = signal<DroneTelemetry[]>([]);
  private readonly _pipelineRuns = signal<PipelineRun[]>([]);
  private readonly _currentFilters = signal<DroneFilters>({});
  private readonly _dronesLoading = signal(false);
  private readonly _pipelineRunsLoading = signal(false);
  private readonly _pipelineRunning = signal(false);
  private readonly _dronesError = signal<string | null>(null);
  private readonly _pipelineError = signal<string | null>(null);

  private readonly _selectedDroneId = signal<string | null>(null);
  private readonly _selectedDroneHistory = signal<DroneTelemetry[]>([]);
  private readonly _historyLoading = signal(false);
  private readonly _historyError = signal<string | null>(null);

  readonly drones = this._drones.asReadonly();
  readonly pipelineRuns = this._pipelineRuns.asReadonly();
  readonly currentFilters = this._currentFilters.asReadonly();
  readonly dronesLoading = this._dronesLoading.asReadonly();
  readonly pipelineRunsLoading = this._pipelineRunsLoading.asReadonly();
  readonly pipelineRunning = this._pipelineRunning.asReadonly();
  readonly dronesError = this._dronesError.asReadonly();
  readonly pipelineError = this._pipelineError.asReadonly();

  readonly selectedDroneId = this._selectedDroneId.asReadonly();
  readonly selectedDroneHistory = this._selectedDroneHistory.asReadonly();
  readonly historyLoading = this._historyLoading.asReadonly();
  readonly historyError = this._historyError.asReadonly();

  /** Called once when the dashboard mounts. The two requests are independent and run in parallel. */
  loadInitial(): void {
    this.refreshDrones();
    this.refreshPipelineRuns();
  }

  /** Called by the filter form on submit. Replaces the remembered filter set and re-fetches drones with it. */
  applyFilters(filters: DroneFilters): void {
    this._currentFilters.set(filters);
    this.refreshDrones();
  }

  /**
   * Always requests the map's one-row-per-drone "current fleet" view (see
   * `DronesApiService.listLatest`). If the currently selected drone is no
   * longer present in the new result (filtered out, or no longer
   * reporting), its selection/path is cleared — keeping a path visible
   * for a marker that's no longer on the map would be confusing.
   */
  refreshDrones(): void {
    this._dronesLoading.set(true);
    this._dronesError.set(null);

    this.dronesApi.listLatest(this._currentFilters()).subscribe({
      next: (page) => {
        this._drones.set(page.items);
        this._dronesLoading.set(false);

        const selectedId = this._selectedDroneId();
        if (selectedId !== null && !page.items.some((drone) => drone.drone_id === selectedId)) {
          this.clearSelection();
        }
      },
      error: (err: HttpErrorResponse) => {
        this._dronesError.set(extractErrorMessage(err));
        this._dronesLoading.set(false);
      },
    });
  }

  refreshPipelineRuns(): void {
    this._pipelineRunsLoading.set(true);

    this.pipelineApi.listRuns().subscribe({
      next: (runs) => {
        this._pipelineRuns.set(runs);
        this._pipelineRunsLoading.set(false);
      },
      error: () => {
        // The runs table simply stays as-is; a failure here isn't surfaced
        // as its own error state to keep this exercise's error UI focused
        // on the two operations the user directly triggers (filtering and
        // running the pipeline).
        this._pipelineRunsLoading.set(false);
      },
    });
  }

  /**
   * Selects a drone and fetches its path history, or — if that drone is
   * already selected — deselects it (a simple, predictable toggle).
   * Selecting a different drone always replaces any previous selection.
   *
   * Stale-response guard: each history request closes over the
   * `droneId` it was made for, and both the success and error callbacks
   * re-check `this._selectedDroneId() === droneId` before applying
   * anything. If the user selects a different drone (or deselects)
   * before this request resolves, a late response for the OLD drone_id
   * is simply dropped — it can never overwrite a newer selection or
   * resurrect history after a deselect.
   */
  selectDrone(droneId: string): void {
    if (this._selectedDroneId() === droneId) {
      this.clearSelection();
      return;
    }

    this._selectedDroneId.set(droneId);
    this._selectedDroneHistory.set([]);
    this._historyLoading.set(true);
    this._historyError.set(null);

    this.dronesApi.getHistory(droneId).subscribe({
      next: (history) => {
        if (this._selectedDroneId() !== droneId) {
          return; // Stale response — selection has since changed.
        }
        this._selectedDroneHistory.set(history);
        this._historyLoading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        if (this._selectedDroneId() !== droneId) {
          return; // Stale response — selection has since changed.
        }
        this._historyError.set(extractErrorMessage(err));
        this._historyLoading.set(false);
      },
    });
  }

  /** Deselects the current drone (if any) and clears its path/history/error state. */
  clearSelection(): void {
    this._selectedDroneId.set(null);
    this._selectedDroneHistory.set([]);
    this._historyLoading.set(false);
    this._historyError.set(null);
  }

  /**
   * Triggers the (currently synchronous) pipeline run. `POST
   * /api/pipeline/run` returns HTTP 200 even when the run's own domain
   * `status` ends up "failed" — only a real HTTP-level failure (network
   * error, HTTP 500) reaches the `error` branch below.
   *
   * Both drones and pipeline runs are refreshed for *every* HTTP-level
   * response, regardless of domain `status`: the backend commits valid
   * telemetry rows individually, so a "failed" run may still have
   * persisted some rows before the failure — refreshing only the run
   * history in that case would leave the map showing stale data.
   */
  runPipeline(): void {
    this._pipelineRunning.set(true);
    this._pipelineError.set(null);

    this.pipelineApi.runPipeline().subscribe({
      next: (run) => {
        this._pipelineRunning.set(false);
        this.refreshDrones();
        this.refreshPipelineRuns();

        if (run.status !== 'completed') {
          // "failed" (or, defensively, any other non-"completed" status):
          // a real, fully persisted domain outcome, not a successful run.
          this._pipelineError.set(run.error_message ?? 'Pipeline run failed.');
        }
      },
      error: (err: HttpErrorResponse) => {
        this._pipelineRunning.set(false);
        this._pipelineError.set(extractErrorMessage(err));
      },
    });
  }
}
