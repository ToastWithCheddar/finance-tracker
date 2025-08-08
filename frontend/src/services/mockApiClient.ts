/**
 * Mock API client for UI development without backend
 */

interface MockApiConfig {
  useMockData: boolean;
  uiOnlyMode: boolean;
  baseURL: string;
}

class MockApiClient {
  private config: MockApiConfig;
  private mockDelay: number = 500; // Simulate network delay

  constructor() {
    this.config = {
      useMockData: import.meta.env.VITE_USE_MOCK_DATA === 'true',
      uiOnlyMode: import.meta.env.VITE_UI_ONLY_MODE === 'true',
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
    };
  }

  private async simulateDelay(ms: number = this.mockDelay): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  get isMockMode(): boolean {
    return this.config.useMockData || this.config.uiOnlyMode;
  }

  private getMockEndpoint(endpoint: string): string {
    // Convert regular API endpoint to mock endpoint
    const mockBasePath = '/api/mock';
    return endpoint.replace('/api', mockBasePath);
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    if (!this.isMockMode) {
      // Use regular API
      const response = await fetch(`${this.config.baseURL}${endpoint}`, options);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    }

    // Use mock API
    await this.simulateDelay();
    
    try {
      const mockEndpoint = this.getMockEndpoint(endpoint);
      const response = await fetch(`${this.config.baseURL}${mockEndpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      });

      if (!response.ok) {
        // If mock endpoint fails, return fallback mock data
        console.warn(`Mock endpoint failed: ${mockEndpoint}, using fallback data`);
        return this.getFallbackMockData<T>(endpoint);
      }

      return response.json();
    } catch (error) {
      console.warn(`Mock API request failed for ${endpoint}, using fallback data:`, error);
      return this.getFallbackMockData<T>(endpoint);
    }
  }

  private getFallbackMockData<T>(endpoint: string): T {
    // Fallback mock data when mock API is not available
    const mockData: Record<string, unknown> = {
      '/auth/me': {
        id: 'user-1',
        email: 'demo@financetracker.dev',
        username: 'demo_user',
        first_name: 'Demo',
        last_name: 'User'
      },
      '/auth/login': {
        access_token: 'mock-token-12345',
        token_type: 'bearer',
        user: {
          id: 'user-1',
          email: 'demo@financetracker.dev',
          username: 'demo_user'
        }
      },
      '/accounts': [
        {
          id: 'acc-1',
          name: 'Chase Checking',
          account_type: 'checking',
          balance_cents: 245075,
          currency: 'USD'
        },
        {
          id: 'acc-2',
          name: 'Savings Account',
          account_type: 'savings',
          balance_cents: 892550,
          currency: 'USD'
        }
      ],
      '/transactions': [
        {
          id: 'txn-1',
          description: 'Starbucks',
          amount_cents: -450,
          transaction_date: new Date().toISOString(),
          category: { name: 'Food & Dining', icon: '🍔' }
        },
        {
          id: 'txn-2',
          description: 'Salary',
          amount_cents: 350000,
          transaction_date: new Date(Date.now() - 86400000).toISOString(),
          category: { name: 'Salary', icon: '💰' }
        }
      ],
      '/categories': [
        { id: 'cat-1', name: 'Food & Dining', icon: '🍔', color: '#FF6B6B' },
        { id: 'cat-2', name: 'Transportation', icon: '🚗', color: '#4ECDC4' },
        { id: 'cat-3', name: 'Salary', icon: '💰', color: '#00B894' }
      ],
      '/budgets': [
        {
          id: 'budget-1',
          category: { name: 'Food & Dining' },
          amount_cents: 50000,
          spent_amount_cents: 32000,
          remaining_amount_cents: 18000
        }
      ],
      '/goals': [
        {
          id: 'goal-1',
          name: 'Emergency Fund',
          target_amount_cents: 1000000,
          current_amount_cents: 650000,
          progress_percentage: 65
        }
      ],
      '/dashboard/summary': {
        total_balance: 11375.25,
        monthly_spending: 2340.50,
        monthly_income: 3500.00,
        net_worth: 11375.25
      }
    };

    // Handle parameterized endpoints
    for (const [path, data] of Object.entries(mockData)) {
      if (endpoint.startsWith(path) || endpoint === path) {
        return data as T;
      }
    }

    // Default fallback
    return {
      message: 'Mock data not available for this endpoint',
      endpoint,
      mockMode: true
    } as T;
  }

  // Convenience methods
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data: Record<string, unknown>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async put<T>(endpoint: string, data: Record<string, unknown>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // Development helpers
  enableMockMode(): void {
    this.config.useMockData = true;
    console.log('🎭 Mock mode enabled for UI development');
  }

  disableMockMode(): void {
    this.config.useMockData = false;
    console.log('🌐 Mock mode disabled, using real API');
  }

  setMockDelay(ms: number): void {
    this.mockDelay = ms;
    console.log(`⏱️ Mock API delay set to ${ms}ms`);
  }

  getStatus(): MockApiConfig & { mockDelay: number } {
    return {
      ...this.config,
      mockDelay: this.mockDelay
    };
  }
}

// Create singleton instance
export const mockApiClient = new MockApiClient();

// Export for use in development console
if (import.meta.env.DEV) {
  (window as unknown as { mockApiClient: MockApiClient }).mockApiClient = mockApiClient;
  console.log('🛠️ Mock API client available at window.mockApiClient');
}