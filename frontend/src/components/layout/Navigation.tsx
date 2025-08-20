import { NavLink, useLocation } from 'react-router-dom';
import { navigationItems } from '../../config/navigation';
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
                {navigationItems.map((item) => (
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

