import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { setSentry } from './utils/logger'

const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;

if (dsn) {
  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration(),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
  // Hand the Sentry SDK off to the prod-safe logger wrapper.
  setSentry({
    addBreadcrumb: (b) => Sentry.addBreadcrumb(b as Sentry.Breadcrumb),
    captureException: (e, ctx) => Sentry.captureException(e, ctx as Parameters<typeof Sentry.captureException>[1]),
    captureMessage: (m, ctx) => Sentry.captureMessage(m, ctx as Parameters<typeof Sentry.captureMessage>[1]),
  });
}

// The Sentry boundary captures unhandled errors for reporting; the inner
// ErrorBoundary renders the existing in-app fallback UI.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Sentry.ErrorBoundary fallback={<ErrorBoundary><></></ErrorBoundary>}>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </Sentry.ErrorBoundary>
  </StrictMode>,
)
