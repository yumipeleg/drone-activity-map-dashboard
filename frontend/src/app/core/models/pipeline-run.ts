/**
 * Mirrors the backend's `PipelineRunRead` response schema exactly
 * (backend/app/schemas/pipeline_run.py) — used for the response of
 * `POST /api/pipeline/run`, `GET /api/pipeline/runs`, and
 * `GET /api/pipeline/runs/{id}` alike, since the backend returns the same
 * shape from all three.
 */
export type PipelineRunStatus = 'queued' | 'started' | 'completed' | 'failed';

export interface PipelineRun {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: PipelineRunStatus;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  error_message: string | null;
  input_file: string | null;
}
