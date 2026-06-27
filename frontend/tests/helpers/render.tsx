import { ReactElement, ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

export function makeTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface ProvidersProps {
  children: ReactNode;
  client?: QueryClient;
  initialEntries?: string[];
}

function Providers({ children, client, initialEntries = ['/'] }: ProvidersProps) {
  const qc = client ?? makeTestQueryClient();
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  options?: RenderOptions & { client?: QueryClient; initialEntries?: string[] },
) {
  const { client, initialEntries, ...rtl } = options ?? {};
  return render(ui, {
    wrapper: ({ children }) => (
      <Providers client={client} initialEntries={initialEntries}>
        {children}
      </Providers>
    ),
    ...rtl,
  });
}
