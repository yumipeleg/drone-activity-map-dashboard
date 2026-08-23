import { HttpErrorResponse } from '@angular/common/http';

const GENERIC_MESSAGE = 'Something went wrong. Please try again.';

/**
 * Extracts a user-facing message from an HTTP-level error. FastAPI's
 * default error body shape is `{"detail": "..."}` (a string for most
 * errors, or an array of validation issues for a 422) — this only ever
 * surfaces the string form, since a raw validation array isn't meant for
 * end users.
 */
export function extractErrorMessage(err: HttpErrorResponse): string {
  const detail = (err.error as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string' && detail.trim().length > 0) {
    return detail;
  }
  return GENERIC_MESSAGE;
}
