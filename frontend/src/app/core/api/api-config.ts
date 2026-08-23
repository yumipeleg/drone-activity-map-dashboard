/**
 * The FastAPI backend's own CORS config already allows this exact origin
 * (backend/app/config.py's `cors_allowed_origins`), so a dev-server proxy
 * isn't needed. One plain constant is simpler than wiring up Angular's
 * `environments`/`fileReplacements` mechanism for a single value.
 */
export const API_BASE_URL = 'http://localhost:8000';
