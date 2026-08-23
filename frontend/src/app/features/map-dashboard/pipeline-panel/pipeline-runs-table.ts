import { DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { DashboardStateService } from '../dashboard-state';

/** Read-only history table for GET /api/pipeline/runs. */
@Component({
  selector: 'app-pipeline-runs-table',
  imports: [DatePipe],
  templateUrl: './pipeline-runs-table.html',
  styleUrl: './pipeline-runs-table.css',
})
export class PipelineRunsTable {
  protected readonly state = inject(DashboardStateService);
}
