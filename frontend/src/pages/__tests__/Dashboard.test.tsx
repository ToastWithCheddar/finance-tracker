import { render, screen } from '../../__tests__/utils/testUtils';
import { Dashboard } from '../Dashboard';
import { useDashboardAnalytics } from '../../hooks/useDashboardAnalytics';
import { useWebSocket } from '../../hooks/useWebSocket';

// Mock the hooks
jest.mock('../../hooks/useDashboardAnalytics');
jest.mock('../../hooks/useWebSocket');

const mockUseDashboardAnalytics = useDashboardAnalytics as jest.MockedFunction<typeof useDashboardAnalytics>;
const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;

// Mock data
const mockDashboardData = {
  totalBalance: 5000.50,
  totalTransactions: 125,
  recentTransactions: [
    {
      id: '1',
      description: 'Coffee Shop',
      amountCents: -450,
      date: '2025-08-12',
    },
    {
      id: '2',
      description: 'Salary Deposit',
      amountCents: 300000,
      date: '2025-08-11',
    },
  ],
  spendingByCategory: {
    'Food & Dining': 125000,
    'Transportation': 85000,
    'Entertainment': 45000,
  },
};

describe('Dashboard', () => {
  beforeEach(() => {
    mockUseWebSocket.mockReturnValue(undefined);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should display loading skeleton when data is loading', () => {
      mockUseDashboardAnalytics.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        refetch: jest.fn(),
      });

      render(<Dashboard />);

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getAllByRole('generic', { hidden: true })).toHaveLength(4);
    });
  });

  describe('Error State', () => {
    it('should display error message when there is an error', () => {
      const mockError = new Error('Failed to fetch dashboard data');
      mockUseDashboardAnalytics.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: mockError,
        isError: true,
        refetch: jest.fn(),
      });

      render(<Dashboard />);

      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText(/Failed to load dashboard data/)).toBeInTheDocument();
      expect(screen.getByText(/Failed to fetch dashboard data/)).toBeInTheDocument();
    });

    it('should display generic error message when error has no message', () => {
      mockUseDashboardAnalytics.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: null,
        isError: true,
        refetch: jest.fn(),
      });

      render(<Dashboard />);

      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText(/Please try again later/)).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    beforeEach(() => {
      mockUseDashboardAnalytics.mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: jest.fn(),
      });
    });

    it('should display dashboard title', () => {
      render(<Dashboard />);
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    it('should display key metrics cards', () => {
      render(<Dashboard />);
      
      expect(screen.getByText('Total Balance')).toBeInTheDocument();
      expect(screen.getByText('$5,000.50')).toBeInTheDocument();
      
      expect(screen.getByText('Total Transactions')).toBeInTheDocument();
      expect(screen.getByText('125')).toBeInTheDocument();
    });

    it('should display recent transactions', () => {
      render(<Dashboard />);
      
      expect(screen.getByText('Recent Transactions')).toBeInTheDocument();
      expect(screen.getByText('Coffee Shop')).toBeInTheDocument();
      expect(screen.getByText('Salary Deposit')).toBeInTheDocument();
      expect(screen.getByText('-$4.50')).toBeInTheDocument();
      expect(screen.getByText('$3,000.00')).toBeInTheDocument();
    });

    it('should display spending by category', () => {
      render(<Dashboard />);
      
      expect(screen.getByText('Top Spending by Category')).toBeInTheDocument();
      expect(screen.getByText('Food & Dining')).toBeInTheDocument();
      expect(screen.getByText('Transportation')).toBeInTheDocument();
      expect(screen.getByText('Entertainment')).toBeInTheDocument();
      expect(screen.getByText('$1,250.00')).toBeInTheDocument();
      expect(screen.getByText('$850.00')).toBeInTheDocument();
      expect(screen.getByText('$450.00')).toBeInTheDocument();
    });

    it('should initialize WebSocket connection', () => {
      render(<Dashboard />);
      expect(mockUseWebSocket).toHaveBeenCalledTimes(1);
    });
  });

  describe('Empty Data State', () => {
    it('should display empty state for no recent transactions', () => {
      mockUseDashboardAnalytics.mockReturnValue({
        data: { ...mockDashboardData, recentTransactions: [] },
        isLoading: false,
        error: null,
        isError: false,
        refetch: jest.fn(),
      });

      render(<Dashboard />);
      expect(screen.getByText('No recent transactions.')).toBeInTheDocument();
    });

    it('should display empty state for no spending data', () => {
      mockUseDashboardAnalytics.mockReturnValue({
        data: { ...mockDashboardData, spendingByCategory: {} },
        isLoading: false,
        error: null,
        isError: false,
        refetch: jest.fn(),
      });

      render(<Dashboard />);
      expect(screen.getByText('No spending data available.')).toBeInTheDocument();
    });
  });

  describe('Data Formatting', () => {
    beforeEach(() => {
      mockUseDashboardAnalytics.mockReturnValue({
        data: mockDashboardData,
        isLoading: false,
        error: null,
        isError: false,
        refetch: jest.fn(),
      });
    });

    it('should format currency values correctly', () => {
      render(<Dashboard />);
      
      // Total balance should be formatted as currency
      expect(screen.getByText('$5,000.50')).toBeInTheDocument();
      
      // Transaction amounts should be formatted with proper signs
      expect(screen.getByText('-$4.50')).toBeInTheDocument();
      expect(screen.getByText('$3,000.00')).toBeInTheDocument();
    });

    it('should format transaction count with locale string', () => {
      render(<Dashboard />);
      expect(screen.getByText('125')).toBeInTheDocument();
    });

    it('should format dates correctly', () => {
      render(<Dashboard />);
      // Dates should be formatted as locale date strings
      expect(screen.getByText('8/12/2025')).toBeInTheDocument();
      expect(screen.getByText('8/11/2025')).toBeInTheDocument();
    });
  });
});