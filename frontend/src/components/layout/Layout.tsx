import { Navigation } from './Navigation';
import { ActivityFeed } from './ActivityFeed';

interface LayoutProps {
  children: React.ReactNode;
  showNavigation?: boolean;
  showActivityFeed?: boolean;
}

export function Layout({ children, showNavigation = true, showActivityFeed = true }: LayoutProps) {
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'hsl(var(--bg))' }}>
      {showNavigation && <Navigation />}
      <div className="flex">
        {/* Main content area */}
        <main className={`flex-1 ${showNavigation ? 'pt-0' : ''} relative z-10`}>
          <div className="container mx-auto px-4 py-6">
            {children}
          </div>
        </main>
        
        {/* Activity feed sidebar */}
        {showActivityFeed && (
          <aside className="hidden lg:block w-80 flex-shrink-0 p-4">
            <div className="sticky top-20">
              <ActivityFeed maxItems={15} />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}