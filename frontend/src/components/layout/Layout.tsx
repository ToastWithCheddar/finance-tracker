import { Navigation } from './Navigation';

interface LayoutProps {
  children: React.ReactNode;
  showNavigation?: boolean;
}

export function Layout({ children, showNavigation = true }: LayoutProps) {
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'hsl(var(--bg))' }}>
      {showNavigation && <Navigation />}
      <main className={`${showNavigation ? 'pt-0' : ''}`}>
        <div className="container mx-auto px-4 py-6">
          {children}
        </div>
      </main>
    </div>
  );
}