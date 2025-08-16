import { Transaction, Category, Budget, Goal } from '@/types';

// Mock Transaction Factory
export const createMockTransaction = (overrides: Partial<Transaction> = {}): Transaction => ({
  id: 'mock-transaction-1',
  user_id: 'mock-user-1',
  account_id: 'mock-account-1',
  amount: 25.50,
  description: 'Coffee Shop',
  date: '2025-08-12',
  category_id: 'mock-category-1',
  category: createMockCategory(),
  created_at: '2025-08-12T10:30:00Z',
  updated_at: '2025-08-12T10:30:00Z',
  ml_confidence: 0.85,
  ...overrides,
});

// Mock Category Factory
export const createMockCategory = (overrides: Partial<Category> = {}): Category => ({
  id: 'mock-category-1',
  name: 'Food & Dining',
  color: '#ff6b6b',
  parent_id: null,
  user_id: 'mock-user-1',
  created_at: '2025-08-12T10:00:00Z',
  updated_at: '2025-08-12T10:00:00Z',
  ...overrides,
});

// Mock Budget Factory
export const createMockBudget = (overrides: Partial<Budget> = {}): Budget => ({
  id: 'mock-budget-1',
  user_id: 'mock-user-1',
  category_id: 'mock-category-1',
  category: createMockCategory(),
  name: 'Monthly Food Budget',
  amount: 500.00,
  spent: 250.00,
  period: 'monthly',
  start_date: '2025-08-01',
  end_date: '2025-08-31',
  created_at: '2025-08-01T00:00:00Z',
  updated_at: '2025-08-12T10:30:00Z',
  ...overrides,
});

// Mock Goal Factory
export const createMockGoal = (overrides: Partial<Goal> = {}): Goal => ({
  id: 'mock-goal-1',
  user_id: 'mock-user-1',
  name: 'Emergency Fund',
  description: 'Build emergency fund for unexpected expenses',
  target_amount: 10000.00,
  current_amount: 5000.00,
  target_date: '2025-12-31',
  priority: 'high',
  status: 'active',
  category: 'savings',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-08-12T10:30:00Z',
  ...overrides,
});

// Mock Analytics Data Factory
export const createMockAnalytics = () => ({
  totalIncome: 5000.00,
  totalExpenses: 3500.00,
  netIncome: 1500.00,
  categoryBreakdown: [
    { category: 'Food & Dining', amount: 800.00, percentage: 22.8 },
    { category: 'Transportation', amount: 600.00, percentage: 17.1 },
    { category: 'Utilities', amount: 400.00, percentage: 11.4 },
  ],
  monthlyComparison: [
    { month: 'Jul', income: 4800.00, expenses: 3200.00 },
    { month: 'Aug', income: 5000.00, expenses: 3500.00 },
  ],
  trendData: [
    { date: '2025-08-01', amount: 100.00 },
    { date: '2025-08-02', amount: 150.00 },
    { date: '2025-08-03', amount: 75.00 },
  ],
});

// Mock Zustand Store States
export const createMockRealtimeState = () => ({
  isConnected: true,
  connectionStatus: 'connected' as const,
  recentTransactions: [
    createMockTransaction({ id: 'recent-1', description: 'Recent Transaction 1' }),
    createMockTransaction({ id: 'recent-2', description: 'Recent Transaction 2' }),
  ],
  transactionUpdates: [],
  milestoneAlerts: [],
  goalCompletions: [],
  goalUpdates: [],
  notifications: [
    {
      id: 'notif-1',
      type: 'budget_alert',
      title: 'Budget Alert',
      message: 'You have exceeded 80% of your food budget',
      timestamp: '2025-08-12T10:30:00Z',
      read: false,
      priority: 'medium' as const,
    },
  ],
  budgetAlerts: [],
});

export const createMockAuthState = () => ({
  user: {
    id: 'mock-user-1',
    email: 'test@example.com',
    display_name: 'Test User',
    avatar_url: null,
  },
  isAuthenticated: true,
  isLoading: false,
  error: null,
});

// Mock Hook Return Values
export const createMockUseDashboardAnalytics = () => ({
  data: createMockAnalytics(),
  isLoading: false,
  error: null,
  refetch: jest.fn(),
});

export const createMockUseBudgets = () => ({
  data: [
    createMockBudget({ id: 'budget-1', name: 'Food Budget' }),
    createMockBudget({ id: 'budget-2', name: 'Transport Budget', category_id: 'cat-2' }),
  ],
  isLoading: false,
  error: null,
  refetch: jest.fn(),
});

export const createMockUseTransactions = () => ({
  data: {
    data: [
      createMockTransaction({ id: 'trans-1', description: 'Transaction 1' }),
      createMockTransaction({ id: 'trans-2', description: 'Transaction 2' }),
    ],
    pagination: {
      page: 1,
      limit: 20,
      total: 2,
      totalPages: 1,
    },
  },
  isLoading: false,
  error: null,
  refetch: jest.fn(),
});