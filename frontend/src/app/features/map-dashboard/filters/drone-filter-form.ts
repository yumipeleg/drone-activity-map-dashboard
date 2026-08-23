import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { DashboardStateService } from '../dashboard-state';
import { DroneFilters } from '../../../core/models/drone-filters';
import { DroneStatus } from '../../../core/models/drone-telemetry';

/**
 * The "Drone filters" panel from the dashboard layout. Named
 * `DroneFilterForm` (not `DroneFilters`, the requested component name) to
 * avoid colliding with the `DroneFilters` TypeScript interface it imports —
 * same responsibility, a slightly more precise name (it IS a form).
 *
 * Filtering always goes through the backend: submitting calls
 * `DashboardStateService.applyFilters()`, which re-fetches
 * `GET /api/drones` with the new query params. Nothing here filters an
 * already-loaded drone array locally.
 */
@Component({
  selector: 'app-drone-filter-form',
  imports: [ReactiveFormsModule],
  templateUrl: './drone-filter-form.html',
  styleUrl: './drone-filter-form.css',
})
export class DroneFilterForm {
  private readonly fb = inject(FormBuilder);
  protected readonly state = inject(DashboardStateService);

  protected readonly form = this.fb.group({
    droneType: this.fb.control<string | null>(null),
    status: this.fb.control<DroneStatus | null>(null),
    operatorId: this.fb.control<string | null>(null),
    minBattery: this.fb.control<number | null>(null),
    from: this.fb.control<string | null>(null),
    to: this.fb.control<string | null>(null),
  });

  protected applyFilters(): void {
    const raw = this.form.getRawValue();
    const filters: DroneFilters = {
      droneType: raw.droneType ?? undefined,
      status: raw.status ?? undefined,
      operatorId: raw.operatorId ?? undefined,
      minBattery: raw.minBattery ?? undefined,
      from: raw.from ?? undefined,
      to: raw.to ?? undefined,
    };
    this.state.applyFilters(filters);
  }

  protected clearFilters(): void {
    this.form.reset();
    this.state.applyFilters({});
  }
}
