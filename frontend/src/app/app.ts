import { Component } from '@angular/core';
import { MapDashboard } from './features/map-dashboard/map-dashboard';

@Component({
  selector: 'app-root',
  imports: [MapDashboard],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {}
