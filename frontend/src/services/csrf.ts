/**
 * CSRF protection — double-submit cookie strategy (FE-SEC-002).
 *
 * The backend (`backend/app/main.py` `csrf_double_submit` middleware) issues a
 * `csrf_token` cookie on every safe-method response. That cookie is NOT
 * HttpOnly so this module can read it and copy the value into the
 * `X-CSRF-Token` header on every mutating request. The backend then verifies
 * `cookie == header`. There is no client-generated token anymore.
 *
 * See `docs/runbooks/csrf-strategy.md` for the full design.
 */

const TOKEN_HEADER = 'X-CSRF-Token';
const TOKEN_COOKIE = 'csrf_token';

function readCookie(name: string): string | null {
  if (typeof document === 'undefined' || !document.cookie) return null;
  const target = `${name}=`;
  for (const part of document.cookie.split(';')) {
    const trimmed = part.trim();
    if (trimmed.startsWith(target)) {
      return decodeURIComponent(trimmed.slice(target.length));
    }
  }
  return null;
}

class CSRFService {
  /**
   * Read the current CSRF token from the cookie, if any. Returns an empty
   * string when no cookie is present (e.g. before the first GET request).
   */
  getToken(): string {
    return readCookie(TOKEN_COOKIE) ?? '';
  }

  /**
   * Headers to attach to mutating requests. When no cookie is present we
   * omit the header rather than send an empty one — the backend treats a
   * missing header as a 403 only on mutating requests, and the SPA always
   * has at least one safe-method round-trip before its first mutation.
   */
  getHeaders(): Record<string, string> {
    const token = this.getToken();
    return token ? { [TOKEN_HEADER]: token } : {};
  }

  /** Login/logout flows used to call this; now a no-op (server owns the cookie). */
  refreshToken(): void {
    // No-op. The backend rotates the cookie on its own schedule.
  }

  /** Cleared by the browser when the cookie expires; nothing to do here. */
  clearToken(): void {
    // No-op.
  }

  /** Compatibility shim for older imports that called this on init. */
  restoreToken(): void {
    // No-op.
  }
}

export const csrfService = new CSRFService();
