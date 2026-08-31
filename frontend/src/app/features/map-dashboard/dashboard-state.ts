import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { EMPTY } from 'rxjs';
import { catchError, finalize, first, switchMap, timer } from 'rxjs';
import { extractErrorMessage } from '../../core/api/http-error';
import { DronesApiService } from '../../core/api/drones-api';
import { PipelineApiService } from '../../core/api/pipeline-api';
import { DroneFilters } from '../../core/models/drone-filters';
import { DroneTelemetry } from '../../core/models/drone-telemetry';
import { PipelineRun, PipelineRunStatus } from '../../core/models/pipeline-run';

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
  private static readonly POLL_MS = 1000;

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

  private readonly _availableInputFiles = signal<string[]>([]);
  private readonly _selectedInputFile = signal<string | null>(null);
  private readonly _inputFilesLoading = signal(false);
  private readonly _inputFilesError = signal<string | null>(null);

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

  readonly availableInputFiles = this._availableInputFiles.asReadonly();
  readonly selectedInputFile = this._selectedInputFile.asReadonly();
  readonly inputFilesLoading = this._inputFilesLoading.asReadonly();
  readonly inputFilesError = this._inputFilesError.asReadonly();

  readonly canRunPipeline = computed(
    () =>
      !this._pipelineRunning() &&
      !this._inputFilesLoading() &&
      this._inputFilesError() === null &&
      this._availableInputFiles().length > 0 &&
      this._selectedInputFile() !== null,
  );

  readonly selectedDroneId = this._selectedDroneId.asReadonly();
  readonly selectedDroneHistory = this._selectedDroneHistory.asReadonly();
  readonly historyLoading = this._historyLoading.asReadonly();
  readonly historyError = this._historyError.asReadonly();

  /** Called once when the dashboard mounts. The requests are independent and run in parallel. */
  loadInitial(): void {
    this.refreshDrones();
    this.refreshPipelineRuns();
    this.loadAvailableInputFiles();
  }

  loadAvailableInputFiles(): void {
    this._inputFilesLoading.set(true);
    this._inputFilesError.set(null);

    this.pipelineApi.listInputs().subscribe({
      next: (response) => {
        this._availableInputFiles.set(response.files);
        this._inputFilesLoading.set(false);

        if (this._selectedInputFile() === null) {
          const preferred =
            response.files.includes(response.default_file)
              ? response.default_file
              : (response.files[0] ?? null);
          this._selectedInputFile.set(preferred);
        }
      },
      error: (err: HttpErrorResponse) => {
        this._inputFilesError.set(extractErrorMessage(err));
        this._availableInputFiles.set([]);
        this._selectedInputFile.set(null);
        this._inputFilesLoading.set(false);
      },
    });
  }

  selectInputFile(filename: string): void {
    this._selectedInputFile.set(filename);
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
   * Accepts a new pipeline run (HTTP 202 + queued) and polls
   * `GET /api/pipeline/runs/{id}` until the run reaches a terminal status.
   *
   * Refreshes drones and pipeline run history once on `completed` or
   * `failed` — the backend may persist partial telemetry before a failed
   * run finishes, so the map must refresh even on failure.
   */
  runPipeline(): void {
    if (!this.canRunPipeline()) {
      return;
    }

    const selectedFile = this._selectedInputFile();
    if (selectedFile === null) {
      return;
    }

    this._pipelineRunning.set(true);
    this._pipelineError.set(null);

    this.pipelineApi
      .runPipeline(selectedFile)
      .pipe(
        switchMap((queuedRun) => {
          this.refreshPipelineRuns();
          return timer(0, DashboardStateService.POLL_MS).pipe(
            switchMap(() => this.pipelineApi.getRun(queuedRun.id)),
            first((run) => !this.isInProgress(run.status)),
          );
        }),
        catchError((err: HttpErrorResponse) => {
          this._pipelineError.set(this.extractPipelineError(err));
          return EMPTY;
        }),
        finalize(() => this._pipelineRunning.set(false)),
      )
      .subscribe((finalRun) => {
        this.refreshDrones();
        this.refreshPipelineRuns();

        if (finalRun.status === 'failed') {
          this._pipelineError.set(finalRun.error_message ?? 'Pipeline run failed.');
        }
      });
  }

  private isInProgress(status: PipelineRunStatus): boolean {
    return status === 'queued' || status === 'started';
  }

  private extractPipelineError(err: HttpErrorResponse): string {
    const body = err.error as Partial<PipelineRun> | null;
    if (typeof body?.error_message === 'string' && body.error_message.trim().length > 0) {
      return body.error_message;
    }
    return extractErrorMessage(err);
  }
}
