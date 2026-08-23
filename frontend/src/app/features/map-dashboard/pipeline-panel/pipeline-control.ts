import { Component, inject } from '@angular/core';
import { DashboardStateService } from '../dashboard-state';

/** The "Run Pipeline" button and its inline running/error feedback. */
@Component({
  selector: 'app-pipeline-control',
  imports: [],
  templateUrl: './pipeline-control.html',
  styleUrl: './pipeline-control.css',
})
export class PipelineControl {
  protected readonly state = inject(DashboardStateService);

  protected runPipeline(): void {
    this.state.runPipeline();
  }
}
