import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardStateService } from '../dashboard-state';
import { PipelineControl } from './pipeline-control';

describe('PipelineControl', () => {
  let runPipeline: ReturnType<typeof vi.fn>;
  let selectInputFile: ReturnType<typeof vi.fn>;
  let canRunPipeline: ReturnType<typeof signal<boolean>>;
  let pipelineRunning: ReturnType<typeof signal<boolean>>;
  let pipelineError: ReturnType<typeof signal<string | null>>;
  let inputFilesError: ReturnType<typeof signal<string | null>>;
  let inputFilesLoading: ReturnType<typeof signal<boolean>>;
  let availableInputFiles: ReturnType<typeof signal<string[]>>;
  let selectedInputFile: ReturnType<typeof signal<string | null>>;

  beforeEach(() => {
    runPipeline = vi.fn();
    selectInputFile = vi.fn();
    canRunPipeline = signal(true);
    pipelineRunning = signal(false);
    pipelineError = signal<string | null>(null);
    inputFilesError = signal<string | null>(null);
    inputFilesLoading = signal(false);
    availableInputFiles = signal(['sample_drones.json']);
    selectedInputFile = signal('sample_drones.json');

    TestBed.configureTestingModule({
      imports: [PipelineControl],
      providers: [
        {
          provide: DashboardStateService,
          useValue: {
            canRunPipeline,
            pipelineRunning,
            pipelineError,
            inputFilesError,
            inputFilesLoading,
            availableInputFiles,
            selectedInputFile,
            runPipeline,
            selectInputFile,
          },
        },
      ],
    });
  });

  it('clicking the button calls DashboardStateService.runPipeline()', () => {
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('button');
    button.click();

    expect(runPipeline).toHaveBeenCalledOnce();
  });

  it('disables the button when canRunPipeline is false', () => {
    canRunPipeline.set(false);
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('button');
    expect(button.disabled).toBe(true);
  });

  it('shows "Running…" while the pipeline is running', () => {
    pipelineRunning.set(true);
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('button');
    expect(button.textContent).toContain('Running…');
  });

  it('changing the select calls selectInputFile()', () => {
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    select.value = 'sample_drones.json';
    select.dispatchEvent(new Event('change'));

    expect(selectInputFile).toHaveBeenCalledWith('sample_drones.json');
  });

  it('shows the input-files error message when set', () => {
    inputFilesError.set('Service unavailable');
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const alerts = fixture.nativeElement.querySelectorAll('[role="alert"]');
    expect(alerts[0].textContent).toContain('Could not load input files');
    expect(alerts[0].textContent).toContain('Service unavailable');
  });

  it('shows the pipeline error message when set', () => {
    pipelineError.set('Input file not found');
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const alerts = fixture.nativeElement.querySelectorAll('[role="alert"]');
    expect(alerts[alerts.length - 1].textContent).toContain('Input file not found');
  });
});
