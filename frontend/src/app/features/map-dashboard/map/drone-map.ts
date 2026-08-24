import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, effect, inject } from '@angular/core';
import { NgStyle } from '@angular/common';
import * as L from 'leaflet';
import { DashboardStateService } from '../dashboard-state';
import { DroneTelemetry } from '../../../core/models/drone-telemetry';
import { buildDronePopupHtml } from './drone-popup';
import { computeBounds } from './map-bounds';
import { computeHistoryMapView, getHistoryFitBoundsOptions, HistoryMapView, SINGLE_HISTORY_POINT_ZOOM } from './history-map-view';
import {
  getHistoricalPoints,
  getHistoryPointMarkerOptions,
  getHistoryPolylineOptions,
  getSelectedHistoryMessage,
} from './history-render';
import { getMarkerLegendEntries, getMarkerStyle, markerStyleToSwatchCss, MarkerLegendEntry } from './marker-style';

const NEUTRAL_CENTER: L.LatLngExpression = [20, 0];
const NEUTRAL_ZOOM = 2;

const POPUP_OPTIONS: L.PopupOptions = {
  autoPan: true,
  autoClose: true,
  closeOnClick: false,
};

/**
 * The "Drone map" panel. Reads `DashboardStateService.drones()` and
 * `.selectedDroneHistory()` directly (via `effect()`).
 *
 * Fleet markers stay interactive on `markersLayer`. Path/history overlays
 * live on a separate non-interactive `pathLayer` so they never steal clicks
 * from the current-position markers underneath.
 */
@Component({
  selector: 'app-drone-map',
  imports: [NgStyle],
  templateUrl: './drone-map.html',
  styleUrl: './drone-map.css',
})
export class DroneMap implements AfterViewInit, OnDestroy {
  protected readonly state = inject(DashboardStateService);
  protected readonly markerLegend = getMarkerLegendEntries();

  @ViewChild('mapContainer', { static: true })
  private readonly mapContainerRef!: ElementRef<HTMLDivElement>;

  private map: L.Map | null = null;
  private markersLayer: L.LayerGroup | null = null;
  private pathLayer: L.LayerGroup | null = null;
  private readonly markerByDroneId = new Map<string, L.CircleMarker>();
  private pendingPopupHandler: (() => void) | null = null;
  private popupFallbackTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    effect(() => this.renderMarkers(this.state.drones()));
    effect(() => this.renderPath(this.state.selectedDroneId(), this.state.selectedDroneHistory()));
  }

  ngAfterViewInit(): void {
    this.map = L.map(this.mapContainerRef.nativeElement).setView(NEUTRAL_CENTER, NEUTRAL_ZOOM);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(this.map);

    this.markersLayer = L.layerGroup().addTo(this.map);
    this.pathLayer = L.layerGroup().addTo(this.map);
    this.renderMarkers(this.state.drones());
    this.renderPath(this.state.selectedDroneId(), this.state.selectedDroneHistory());
  }

  ngOnDestroy(): void {
    this.cancelPendingPopup();
    this.map?.remove();
    this.map = null;
    this.markersLayer = null;
    this.pathLayer = null;
    this.markerByDroneId.clear();
  }

  protected selectedHistoryMessage(): string | null {
    const droneId = this.state.selectedDroneId();
    if (droneId === null || this.state.historyLoading()) {
      return null;
    }
    return getSelectedHistoryMessage(droneId, this.state.selectedDroneHistory().length);
  }

  protected legendSwatchStyle(entry: MarkerLegendEntry): Record<string, string> {
    return markerStyleToSwatchCss(entry.style);
  }

  private renderMarkers(drones: DroneTelemetry[]): void {
    if (!this.map || !this.markersLayer) {
      return;
    }

    this.markersLayer.clearLayers();
    this.markerByDroneId.clear();
    for (const drone of drones) {
      const marker = L.circleMarker([drone.latitude, drone.longitude], getMarkerStyle(drone))
        .bindPopup(buildDronePopupHtml(drone), POPUP_OPTIONS)
        .on('click', () => {
          marker.closePopup();
          this.state.selectDrone(drone.drone_id);
        })
        .addTo(this.markersLayer);
      this.markerByDroneId.set(drone.drone_id, marker);
    }

    const bounds = computeBounds(drones);
    if (bounds) {
      this.map.fitBounds(bounds, { maxZoom: 12, padding: [30, 30] });
    } else {
      this.map.setView(NEUTRAL_CENTER, NEUTRAL_ZOOM);
    }
  }

  private renderPath(selectedId: string | null, history: DroneTelemetry[]): void {
    if (!this.map || !this.pathLayer) {
      return;
    }

    this.pathLayer.clearLayers();

    if (selectedId === null) {
      this.cancelPendingPopup();
      this.map.closePopup();
      return;
    }

    if (history.length === 0) {
      return;
    }

    const historicalPoints = getHistoricalPoints(history);
    for (const record of historicalPoints) {
      L.circleMarker([record.latitude, record.longitude], getHistoryPointMarkerOptions()).addTo(this.pathLayer);
    }

    if (history.length >= 2) {
      const points: L.LatLngExpression[] = history.map((record) => [record.latitude, record.longitude]);
      L.polyline(points, getHistoryPolylineOptions()).addTo(this.pathLayer);
    }

    const view = computeHistoryMapView(history);
    this.frameHistoryAndOpenPopup(selectedId, view);
  }

  private frameHistoryAndOpenPopup(droneId: string, view: HistoryMapView): void {
    if (!this.map) {
      return;
    }

    this.cancelPendingPopup();

    const openPopupIfStillSelected = (): void => {
      if (this.state.selectedDroneId() !== droneId) {
        return;
      }
      this.markerByDroneId.get(droneId)?.openPopup();
    };

    let completed = false;
    const complete = (): void => {
      if (completed) {
        return;
      }
      completed = true;
      this.clearPopupSchedule();
      openPopupIfStillSelected();
    };

    this.pendingPopupHandler = complete;
    this.map.once('moveend', complete);

    if (view.bounds) {
      this.map.fitBounds(view.bounds, getHistoryFitBoundsOptions());
    } else if (view.center) {
      this.map.setView(view.center, SINGLE_HISTORY_POINT_ZOOM);
    } else {
      this.cancelPendingPopup();
      return;
    }

    // fitBounds/setView may not emit moveend when the view barely changes.
    this.popupFallbackTimer = setTimeout(complete, 350);
  }

  private cancelPendingPopup(): void {
    this.clearPopupSchedule();
  }

  private clearPopupSchedule(): void {
    if (this.popupFallbackTimer !== null) {
      clearTimeout(this.popupFallbackTimer);
      this.popupFallbackTimer = null;
    }
    if (this.map && this.pendingPopupHandler) {
      this.map.off('moveend', this.pendingPopupHandler);
    }
    this.pendingPopupHandler = null;
  }
}
