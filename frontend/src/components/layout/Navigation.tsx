import { NavLink, useLocation } from 'react-router-dom';
import { Button } from '../ui/Button';
import { ThemeToggle } from '../ui';
import { useAuthStore } from '../../stores/authStore';

interface NavigationProps {
  className?: string;
}

export function Navigation({ className = '' }: NavigationProps) {
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/transactions', label: 'Transactions', icon: '💰' },
    { path: '/categories', label: 'Categories', icon: '🏷️' },
    { path: '/budgets', label: 'Budgets', icon: '🎯' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className={`bg-white shadow-sm border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700 ${className}`}>
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <div className="flex items-center space-x-4">
            <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
              💳 Finance Tracker
            </div>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={`
                  px-3 py-2 rounded-md text-sm font-medium transition-colors
                  ${isActive(item.path)
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }
                `}
              >
                <span className="mr-2">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {user && (
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Welcome, {user.displayName ?? user.email.split('@')[0]}
              </div>
            )}
            <ThemeToggle />
            
            <Button
              variant="outline"
              size="sm"
              onClick={logout}
              className="text-red-600 border-red-300 hover:bg-red-50"
            >
              Logout
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden pb-3">
          <div className="flex space-x-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={`
                  flex-1 px-3 py-2 rounded-md text-xs font-medium text-center transition-colors
                  ${isActive(item.path)
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }
                `}
              >
                <div>{item.icon}</div>
                <div>{item.label}</div>
              </NavLink>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}

interface LayoutProps {
  children: React.ReactNode;
  showNavigation?: boolean;
}

export function Layout({ children, showNavigation = true }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {showNavigation && <Navigation />}
      <main className={showNavigation ? 'pt-0' : ''}>
        {children}
      </main>
    </div>
  );
}