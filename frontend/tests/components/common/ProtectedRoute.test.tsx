/**
 * ProtectedRoute — unauth → redirect; authed → renders children.
 *
 * Drives the auth state via the real Zustand store (not a mock) so the
 * component's selector hooks (useIsAuthenticated, useAuthLoading) resolve
 * naturally.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '@/components/common/ProtectedRoute';
import { useAuthStore } from '@/stores/authStore';

afterEach(() => {
  useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false, error: null });
});

function Harness() {
  return (
    <MemoryRouter initialEntries={['/secret']}>
      <Routes>
        <Route path="/login" element={<div>login page</div>} />
        <Route
          path="/secret"
          element={
            <ProtectedRoute>
              <div>secret content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProtectedRoute', () => {
  it('redirects unauthenticated users to /login', () => {
    useAuthStore.setState({ isAuthenticated: false, isLoading: false });
    render(<Harness />);
    expect(screen.getByText('login page')).toBeInTheDocument();
    expect(screen.queryByText('secret content')).toBeNull();
  });

  it('renders children for authenticated users', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 'u-1', email: 't@t.com' } as any,
    });
    render(<Harness />);
    expect(screen.getByText('secret content')).toBeInTheDocument();
  });

  it('shows the loading spinner while auth is resolving', () => {
    useAuthStore.setState({ isAuthenticated: false, isLoading: true });
    const { container } = render(<Harness />);
    // The loading branch renders an animate-spin div instead of redirecting.
    expect(container.querySelector('.animate-spin')).not.toBeNull();
    expect(screen.queryByText('login page')).toBeNull();
  });
});
