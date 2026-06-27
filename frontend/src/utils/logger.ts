/**
 * Production-safe logger wrapper for finance-tracker frontend.
 *
 *
 * Behaviour:
 *  - In dev (`import.meta.env.DEV`) forwards to `console.{level}`.
 *  - In prod, if `import.meta.env.VITE_SENTRY_DSN` is set, routes through Sentry
 *    breadcrumbs (info/debug/warn) and `Sentry.captureException`/`captureMessage`
 *    (error). Otherwise becomes a no-op so we don't ship console noise.
 *
 * Always strips known-sensitive fields (Authorization headers, anything whose
 * key contains "token" / "secret" / "password") from contextual data before
 * emitting — see FE-SEC-004.
 */

// Accept anything callers used to pass to console.* — Record, primitives,
// arrays, Errors, etc. We redact known-sensitive keys when present.
type Ctx = unknown;

const SENSITIVE_KEY_RE = /authorization|token|secret|password/i;

function redact(input: unknown): unknown {
  if (input == null) return input;
  if (Array.isArray(input)) return input.map(redact);
  if (typeof input !== 'object') return input;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(input as Record<string, unknown>)) {
    if (SENSITIVE_KEY_RE.test(k)) {
      out[k] = '[REDACTED]';
    } else if (typeof v === 'object' && v !== null) {
      out[k] = redact(v);
    } else {
      out[k] = v;
    }
  }
  return out;
}

function safeCtx(ctx: Ctx): Ctx {
  if (ctx === undefined || ctx === null) return ctx;
  return redact(ctx);
}

const isDev = (): boolean => {
  try {
    return Boolean((import.meta as ImportMeta & { env?: { DEV?: boolean } }).env?.DEV);
  } catch {
    return false;
  }
};

const sentryDsn = (): string | undefined => {
  try {
    return (import.meta as ImportMeta & { env?: { VITE_SENTRY_DSN?: string } }).env?.VITE_SENTRY_DSN;
  } catch {
    return undefined;
  }
};

type SentryLike = {
  addBreadcrumb: (b: { message: string; data?: unknown; level?: string }) => void;
  captureException: (e: unknown, ctx?: { contexts?: Record<string, unknown> }) => void;
  captureMessage: (m: string, ctx?: { contexts?: Record<string, unknown> }) => void;
};
let sentryHandle: SentryLike | undefined;
export function setSentry(s: SentryLike): void {
  sentryHandle = s;
}

function emit(level: 'debug' | 'info' | 'warn' | 'error', msg: string, ctx?: Ctx, err?: unknown): void {
  const data = safeCtx(ctx);
  if (isDev()) {
    // eslint-disable-next-line no-console
    const fn = (console as unknown as Record<string, (...a: unknown[]) => void>)[level] ?? console.log;
    if (err !== undefined) fn(msg, data, err);
    else if (data !== undefined) fn(msg, data);
    else fn(msg);
    return;
  }
  if (!sentryDsn() || !sentryHandle) return; // no-op in prod without Sentry
  if (level === 'error') {
    const customCtx: Record<string, unknown> =
      data && typeof data === 'object' && !Array.isArray(data)
        ? (data as Record<string, unknown>)
        : data !== undefined
          ? { value: data }
          : {};
    sentryHandle.captureException(err ?? new Error(msg), { contexts: { custom: customCtx } });
  } else {
    sentryHandle.addBreadcrumb({ message: msg, data, level });
  }
}

// Accept variadic extras so that `console.X(msg, a, b, c)` callsites translate
// 1:1. Extras beyond the first context are folded into the context payload.
function foldExtras(primary: Ctx, rest: unknown[]): Ctx {
  if (!rest || rest.length === 0) return primary;
  if (primary === undefined) {
    return rest.length === 1 ? rest[0] : (rest as unknown);
  }
  return { ctx: primary, extras: rest } as unknown;
}

export const logger = {
  debug: (msg: string, ctx?: Ctx, ...rest: unknown[]) => emit('debug', msg, foldExtras(ctx, rest)),
  info: (msg: string, ctx?: Ctx, ...rest: unknown[]) => emit('info', msg, foldExtras(ctx, rest)),
  warn: (msg: string, ctx?: Ctx, ...rest: unknown[]) => emit('warn', msg, foldExtras(ctx, rest)),
  error: (msg: string, err?: unknown, ctx?: Ctx, ...rest: unknown[]) =>
    emit('error', msg, foldExtras(ctx, rest), err),
};

export default logger;
