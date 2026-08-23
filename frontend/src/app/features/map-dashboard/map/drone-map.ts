import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, effect, inject } from '@angular/core';
import * as L from 'leaflet';
import { DashboardStateService } from '../dashboard-state';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import { buildDronePopupHtml } from './drone-popup';
import { computeBounds } from './map-bounds';

// Leaflet's default marker icons are referenced by relative path from its
// own CSS and aren't served by Angular's build automatically. The images
// are copied into public/leaflet/ (served at the app root), and this
// override points the default icon at them once, at module load time.
//
// `imagePath` must be set explicitly here too: Leaflet's IconDefault
// always prepends `this.options.imagePath || IconDefault.imagePath` in
// front of iconUrl/iconRetinaUrl/shadowUrl, even when those are overridden
// below. Left unset, Leaflet auto-detects imagePath by reading the
// computed background-image of leaflet.css's own `.leaflet-default-icon-path`
// rule — which Angular's build rewrites to a hashed asset under `/media/`
// — silently prepending `/media/` in front of the paths below.
L.Icon.Default.mergeOptions({
  imagePath: '/',
  iconUrl: 'leaflet/marker-icon.png',
  iconRetinaUrl: 'leaflet/marker-icon-2x.png',
  shadowUrl: 'leaflet/marker-shadow.png',
});

const NEUTRAL_CENTER: L.LatLngExpression = [20, 0];
const NEUTRAL_ZOOM = 2;

/**
 * The "Drone map" panel. Reads `DashboardStateService.drones()` directly
 * (via `effect()`) instead of an `@Input`, so the parent `MapDashboard`
 * doesn't need to thread the drone list through — see the Phase 3A plan's
 * "what belongs in a signal" discussion.
 */
@Component({
  selector: 'app-drone-map',
  imports: [],
  templateUrl: './drone-map.html',
  styleUrl: './drone-map.css',
})
export class DroneMap implements AfterViewInit, OnDestroy {
  protected readonly state = inject(DashboardStateService);

  @ViewChild('mapContainer', { static: true })
  private readonly mapContainerRef!: ElementRef<HTMLDivElement>;

  private map: L.Map | null = null;
  private markersLayer: L.LayerGroup | null = null;

  constructor() {
    // Re-renders markers whenever the drone list changes. Guarded inside
    // renderMarkers() against running before ngAfterViewInit creates the map.
    effect(() => this.renderMarkers(this.state.drones()));
  }

  ngAfterViewInit(): void {
    this.map = L.map(this.mapContainerRef.nativeElement).setView(NEUTRAL_CENTER, NEUTRAL_ZOOM);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(this.map);

    this.markersLayer = L.layerGroup().addTo(this.map);
    this.renderMarkers(this.state.drones());
  }

  ngOnDestroy(): void {
    // Releases Leaflet's internal DOM listeners/handlers so nothing leaks
    // if this component is ever unmounted while the app is running.
    this.map?.remove();
    this.map = null;
    this.markersLayer = null;
  }

  private renderMarkers(drones: DroneTelemetry[]): void {
    if (!this.map || !this.markersLayer) {
      return; // Effect can fire before ngAfterViewInit creates the map.
    }

    this.markersLayer.clearLayers();
    for (const drone of drones) {
      L.marker([drone.latitude, drone.longitude])
        .bindPopup(buildDronePopupHtml(drone))
        .addTo(this.markersLayer);
    }

    const bounds = computeBounds(drones);
    if (bounds) {
      this.map.fitBounds(bounds, { maxZoom: 12, padding: [30, 30] });
    } else {
      this.map.setView(NEUTRAL_CENTER, NEUTRAL_ZOOM);
    }
  }
}
