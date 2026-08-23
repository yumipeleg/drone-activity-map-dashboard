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
 * API services and the four dashboard components (route -> service ->
 * SQLAlchemy on the backend; here, component -> this service -> API
 * service). No NgRx: plain signals, matching AGENTS.md.
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

  readonly drones = this._drones.asReadonly();
  readonly pipelineRuns = this._pipelineRuns.asReadonly();
  readonly currentFilters = this._currentFilters.asReadonly();
  readonly dronesLoading = this._dronesLoading.asReadonly();
  readonly pipelineRunsLoading = this._pipelineRunsLoading.asReadonly();
  readonly pipelineRunning = this._pipelineRunning.asReadonly();
  readonly dronesError = this._dronesError.asReadonly();
  readonly pipelineError = this._pipelineError.asReadonly();

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

  refreshDrones(): void {
    this._dronesLoading.set(true);
    this._dronesError.set(null);

    this.dronesApi.list(this._currentFilters()).subscribe({
      next: (drones) => {
        this._drones.set(drones);
        this._dronesLoading.set(false);
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
