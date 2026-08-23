import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardStateService } from '../dashboard-state';
import { PipelineControl } from './pipeline-control';

describe('PipelineControl', () => {
  let runPipeline: ReturnType<typeof vi.fn>;
  let pipelineRunning: ReturnType<typeof signal<boolean>>;
  let pipelineError: ReturnType<typeof signal<string | null>>;

  beforeEach(() => {
    runPipeline = vi.fn();
    pipelineRunning = signal(false);
    pipelineError = signal<string | null>(null);

    TestBed.configureTestingModule({
      imports: [PipelineControl],
      providers: [{ provide: DashboardStateService, useValue: { pipelineRunning, pipelineError, runPipeline } }],
    });
  });

  it('clicking the button calls DashboardStateService.runPipeline()', () => {
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('button');
    button.click();

    expect(runPipeline).toHaveBeenCalledOnce();
  });

  it('disables the button and shows "Running…" while the pipeline is running', () => {
    pipelineRunning.set(true);
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('button');
    expect(button.disabled).toBe(true);
    expect(button.textContent).toContain('Running…');
  });

  it('shows the pipeline error message when set', () => {
    pipelineError.set('Input file not found');
    const fixture = TestBed.createComponent(PipelineControl);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain('Input file not found');
  });
});
