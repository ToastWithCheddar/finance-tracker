import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from './services/queryClient';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { AuthInitializer } from './components/common/AuthInitializer';
import { ToastProvider } from './components/ui/Toast';
import { LoadingSpinner } from './components/ui/LoadingSpinner';
import { Login } from './pages/Login';
import { AdminBypassButton } from './components/dev-tools/AdminBypassButton';
import { Layout } from './components/layout/Layout';
import { CommandPalette } from './components/layout/CommandPalette';
import { WebSocketManager } from './components/realtime/WebSocketManager';

// Lazily-loaded route components — each becomes its own chunk so the initial
// bundle only needs Login + critical-path shell. Named exports are wrapped to
// match React.lazy's default-export expectation.
const RealtimeDashboard = lazy(() =>
  import('./components/dashboard/RealtimeDashboard').then((m) => ({ default: m.RealtimeDashboard }))
);
const Profile = lazy(() =>
  import('./pages/Profile').then((m) => ({ default: m.Profile }))
);
const Transactions = lazy(() =>
  import('./pages/Transactions').then((m) => ({ default: m.Transactions }))
);
const Categories = lazy(() =>
  import('./pages/Categories').then((m) => ({ default: m.Categories }))
);
const Budgets = lazy(() =>
  import('./pages/Budgets').then((m) => ({ default: m.Budgets }))
);
const Goals = lazy(() => import('./pages/Goals'));

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <AuthInitializer />
          {/* Global realtime connection manager */}
          <WebSocketManager />
          <Router>
            <div className="App">
              <Suspense
                fallback={
                  <div className="min-h-screen flex items-center justify-center">
                    <LoadingSpinner size="lg" />
                  </div>
                }
              >
                <Routes>
                  {/* Public routes */}
                  <Route path="/login" element={<Login />} />

                  {/* Protected routes — each wrapped in its own ErrorBoundary
                      so a thrown render error inside one route doesn't
                      blank-screen the whole app (FE-PR-002). */}
                  <Route
                    path="/dashboard"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <ErrorBoundary>
                            <RealtimeDashboard />
                          </ErrorBoundary>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/transactions"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <ErrorBoundary>
                            <Transactions />
                          </ErrorBoundary>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />


                  <Route
                    path="/categories"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <ErrorBoundary>
                            <Categories />
                          </ErrorBoundary>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/budgets"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <ErrorBoundary>
                            <Budgets />
                          </ErrorBoundary>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/goals"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <ErrorBoundary>
                            <Goals />
                          </ErrorBoundary>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />



                  <Route
                    path="/profile"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <ErrorBoundary>
                            <Profile />
                          </ErrorBoundary>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />

                  {/* Redirect root to dashboard */}
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />

                  {/* Catch all - redirect to dashboard */}
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </Suspense>
            </div>

            {/* Admin bypass button for development */}
            <AdminBypassButton />
            {/* Command Palette must be inside Router for useNavigate */}
            <CommandPalette />
          </Router>

          {/* React Query Devtools - only in development */}
          {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
