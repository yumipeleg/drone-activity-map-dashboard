import { Component, inject } from '@angular/core';
import { DashboardStateService } from '../dashboard-state';

/** The pipeline input selector, Run Pipeline button, and inline feedback. */
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

  protected onInputFileChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    if (select.value) {
      this.state.selectInputFile(select.value);
    }
  }
}
