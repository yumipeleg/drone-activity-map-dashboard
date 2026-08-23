import { HttpErrorResponse } from '@angular/common/http';
import { describe, expect, it } from 'vitest';
import { extractErrorMessage } from './http-error';

describe('extractErrorMessage', () => {
  it('returns the FastAPI "detail" string when present', () => {
    const err = new HttpErrorResponse({ error: { detail: 'Pipeline run 999 not found' }, status: 404 });
    expect(extractErrorMessage(err)).toBe('Pipeline run 999 not found');
  });

  it('falls back to a generic message when detail is missing', () => {
    const err = new HttpErrorResponse({ error: {}, status: 500 });
    expect(extractErrorMessage(err)).toBe('Something went wrong. Please try again.');
  });

  it('falls back to a generic message when detail is a validation array (422), not a string', () => {
    const err = new HttpErrorResponse({
      error: { detail: [{ msg: 'Input should be less than or equal to 100' }] },
      status: 422,
    });
    expect(extractErrorMessage(err)).toBe('Something went wrong. Please try again.');
  });

  it('falls back to a generic message when the response body is not JSON', () => {
    const err = new HttpErrorResponse({ error: null, status: 0 });
    expect(extractErrorMessage(err)).toBe('Something went wrong. Please try again.');
  });
});
