import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { LoginForm } from '../components/auth/LoginForm';
import { RegisterForm } from '../components/auth/RegisterForm';
import { useIsAuthenticated } from '../stores/authStore';

export function Login() {
  const [isLoginMode, setIsLoginMode] = useState(true);
  const isAuthenticated = useIsAuthenticated();

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="mx-auto h-12 w-12 bg-primary-600 rounded-xl flex items-center justify-center">
            <svg
              className="h-8 w-8 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
              />
            </svg>
          </div>
          <h1 className="mt-4 text-3xl font-bold text-gray-900 dark:text-gray-100">
            Finance Tracker
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Take control of your financial future
          </p>
        </div>

        {/* Auth Form Container */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
          {isLoginMode ? (
            <LoginForm
              onSuccess={() => {
                // Navigation is handled by the auth store
              }}
              onSwitchToRegister={() => setIsLoginMode(false)}
            />
          ) : (
            <RegisterForm
              onSuccess={() => {
                // Navigation is handled by the auth store
              }}
              onSwitchToLogin={() => setIsLoginMode(true)}
            />
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>&copy; 2024 Finance Tracker. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
}