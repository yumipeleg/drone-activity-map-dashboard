import { Component, OnInit, inject } from '@angular/core';
import { DashboardStateService } from './dashboard-state';
import { DroneFilterForm } from './filters/drone-filter-form';
import { DroneMap } from './map/drone-map';
import { PipelineControl } from './pipeline-panel/pipeline-control';
import { PipelineRunsTable } from './pipeline-panel/pipeline-runs-table';

/**
 * Thin page/container component: lays out the four dashboard panels and
 * kicks off the initial load. It holds no state of its own — everything
 * lives in `DashboardStateService`, which each child reads directly.
 */
@Component({
  selector: 'app-map-dashboard',
  imports: [DroneFilterForm, DroneMap, PipelineControl, PipelineRunsTable],
  templateUrl: './map-dashboard.html',
  styleUrl: './map-dashboard.css',
})
export class MapDashboard implements OnInit {
  private readonly state = inject(DashboardStateService);

  ngOnInit(): void {
    this.state.loadInitial();
  }
}
