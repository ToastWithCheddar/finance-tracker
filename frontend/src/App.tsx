import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from './services/queryClient';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { AuthInitializer } from './components/common/AuthInitializer';
import { ToastProvider } from './components/ui/Toast';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Settings } from './pages/Settings';
import { Profile } from './pages/Profile';
import { Transactions } from './pages/Transactions';
import { Recurring } from './pages/Recurring';
import { Categories } from './pages/Categories';
import { Budgets } from './pages/Budgets';
import Goals from './pages/Goals';
import { Timeline } from './pages/Timeline';
import { AdminBypassButton } from './components/dev-tools/AdminBypassButton';
import { Layout } from './components/layout/Layout';
import { CommandPalette } from './components/layout/CommandPalette';

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <AuthInitializer />
          <Router>
            <div className="App">
              <Routes>
                {/* Public routes */}
                <Route path="/login" element={<Login />} />
                
                {/* Protected routes */}
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Dashboard />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/transactions"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Transactions />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/recurring"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Recurring />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/categories"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Categories />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/budgets"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Budgets />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/goals"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Goals />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/timeline"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Timeline />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/settings"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Settings />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Layout>
                        <Profile />
                      </Layout>
                    </ProtectedRoute>
                  }
                />
                
                {/* Redirect root to dashboard */}
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                
                {/* Catch all - redirect to dashboard */}
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
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