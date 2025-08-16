import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, ReceiptText, RefreshCcw, Tags, Wallet, Target, CalendarClock, Lightbulb, Settings as SettingsIcon } from 'lucide-react';
import { ConnectionStatusChip, DateChip, NotificationsBell, ProfileMenu } from './TopBarExtras';
import { TickerSummary } from './TickerSummary';
import { ThemeToggle } from '../ui/ThemeToggle';
import { useAuthStore } from '../../stores/authStore';

interface NavigationProps {
  className?: string;
}

export function Navigation({ className = '' }: NavigationProps) {
  const location = useLocation();
  useAuthStore();

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, description: 'Overview of balances, trends, and live updates', color: 'text-blue-600 dark:text-blue-400', hoverColor: 'hover:bg-blue-50 dark:hover:bg-blue-900/30' },
    { path: '/transactions', label: 'Transactions', icon: ReceiptText, description: 'Browse, filter, and manage your transactions', color: 'text-green-600 dark:text-green-400', hoverColor: 'hover:bg-green-50 dark:hover:bg-green-900/30' },
    { path: '/recurring', label: 'Recurring', icon: RefreshCcw, description: 'Configure recurring transactions and rules', color: 'text-purple-600 dark:text-purple-400', hoverColor: 'hover:bg-purple-50 dark:hover:bg-purple-900/30' },
    { path: '/categories', label: 'Categories', icon: Tags, description: 'Organize and maintain your spending categories', color: 'text-orange-600 dark:text-orange-400', hoverColor: 'hover:bg-orange-50 dark:hover:bg-orange-900/30' },
    { path: '/budgets', label: 'Budgets', icon: Wallet, description: 'Create budgets and track progress', color: 'text-red-600 dark:text-red-400', hoverColor: 'hover:bg-red-50 dark:hover:bg-red-900/30' },
    { path: '/goals', label: 'Goals', icon: Target, description: 'Plan and monitor financial goals', color: 'text-yellow-600 dark:text-yellow-400', hoverColor: 'hover:bg-yellow-50 dark:hover:bg-yellow-900/30' },
    { path: '/timeline', label: 'Timeline', icon: CalendarClock, description: 'See a chronological view of key financial events', color: 'text-indigo-600 dark:text-indigo-400', hoverColor: 'hover:bg-indigo-50 dark:hover:bg-indigo-900/30' },
    { path: '/insights', label: 'Insights', icon: Lightbulb, description: 'AI-driven insights and recommendations', color: 'text-pink-600 dark:text-pink-400', hoverColor: 'hover:bg-pink-50 dark:hover:bg-pink-900/30' },
    { path: '/settings', label: 'Settings', icon: SettingsIcon, description: 'Personal settings and preferences', color: 'text-gray-600 dark:text-gray-400', hoverColor: 'hover:bg-gray-50 dark:hover:bg-gray-700' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className={`
      sticky top-0 z-50 bg-[hsl(var(--surface)/0.7)] backdrop-blur-xl border-b border-border shadow-md ${className}
    `}>
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <div className="flex items-center space-x-3">
            <div className="text-xl md:text-2xl font-extrabold tracking-tight bg-gradient-to-r from-[hsl(var(--brand))] via-emerald-400 to-teal-400 bg-clip-text text-transparent">
              Finance Tracker
            </div>
          </div>

          {/* Primary header keeps brand and user actions only */}

          {/* User Menu and global controls */}
          <div className="flex items-center space-x-3 flex-1 justify-end">
            <TickerSummary />
            <ConnectionStatusChip />
            <DateChip />
            <NotificationsBell />
            <ThemeToggle />
            <ProfileMenu />
          </div>
        </div>

        {/* Sub-navigation: scrollable page pills under the main header */}
        <div className="border-t border-border bg-[hsl(var(--surface)/0.6)]">
          <div className="max-w-7xl mx-auto px-3">
            <div className="overflow-x-auto">
              <div className="flex items-center justify-center gap-2 whitespace-nowrap py-2 min-w-max mx-auto">
                {navItems.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    title={item.description}
                    className={`
                      flex items-center gap-2 px-3 py-2 rounded-full text-sm transition-colors flex-shrink-0
                      ${isActive(item.path)
                        ? 'bg-[hsl(var(--brand)/0.12)] text-[hsl(var(--brand))] border border-[hsl(var(--brand)/0.35)]'
                        : 'bg-[hsl(var(--surface))] text-text border border-[hsl(var(--border))] hover:bg-[hsl(var(--border)/0.25)]'
                      }
                    `}
                  >
                    <item.icon className="h-4 w-4 opacity-80" />
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
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
    <div className="min-h-screen" style={{ backgroundColor: 'hsl(var(--bg))' }}>
      {showNavigation && <Navigation />}
      <main className={`${showNavigation ? 'pt-0' : ''} relative z-10`}>
        <div className="container mx-auto px-4 py-6">
          {children}
        </div>
      </main>
    </div>
  );
}