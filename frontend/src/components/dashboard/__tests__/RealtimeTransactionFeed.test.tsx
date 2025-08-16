import { render, screen, fireEvent } from '../../../__tests__/utils/testUtils';
import { RealtimeTransactionFeed } from '../RealtimeTransactionFeed';
import { useRealtimeStore } from '../../../stores/realtimeStore';
import type { RealtimeTransaction } from '../../../stores/realtimeStore';

// Mock the realtime store
jest.mock('../../../stores/realtimeStore');

const mockUseRealtimeStore = useRealtimeStore as jest.MockedFunction<typeof useRealtimeStore>;

// Mock utils
jest.mock('../../../utils', () => ({
  formatCurrency: (amount: number) => `$${(amount / 100).toFixed(2)}`,
  formatRelativeTime: (timestamp: string) => '2 minutes ago',
}));

const createMockTransaction = (overrides: Partial<RealtimeTransaction> = {}): RealtimeTransaction => ({
  id: 'mock-trans-1',
  description: 'Coffee Shop Purchase',
  amountCents: -450,
  is_income: false,
  category_name: 'Food & Dining',
  category_emoji: '🍕',
  merchant: 'Coffee Corner',
  account_name: 'Checking Account',
  created_at: '2025-08-12T10:30:00Z',
  createdAt: '2025-08-12T10:30:00Z',
  isNew: false,
  ...overrides,
});

describe('RealtimeTransactionFeed', () => {
  const mockMarkTransactionsSeen = jest.fn();
  const mockClearOldTransactions = jest.fn();

  beforeEach(() => {
    mockUseRealtimeStore.mockReturnValue({
      markTransactionsSeen: mockMarkTransactionsSeen,
      clearOldTransactions: mockClearOldTransactions,
      // Other store properties aren't used in this component
      isConnected: true,
      connectionStatus: 'connected',
      recentTransactions: [],
      transactionUpdates: [],
      milestoneAlerts: [],
      goalCompletions: [],
      goalUpdates: [],
      notifications: [],
      budgetAlerts: [],
      updateConnectionStatus: jest.fn(),
      addRecentTransaction: jest.fn(),
      addNotification: jest.fn(),
      markNotificationRead: jest.fn(),
      handleWebSocketMessage: jest.fn(),
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Empty State', () => {
    it('should display empty state when no transactions', () => {
      render(<RealtimeTransactionFeed transactions={[]} newCount={0} />);

      expect(screen.getByText('Recent Transactions')).toBeInTheDocument();
      expect(screen.getByText('Live')).toBeInTheDocument();
      expect(screen.getByText('Waiting for transactions...')).toBeInTheDocument();
      expect(screen.getByText('Your real-time transactions will appear here as they happen.')).toBeInTheDocument();

      // Check for live indicator
      const liveIndicator = screen.getByText('Live').previousSibling;
      expect(liveIndicator).toHaveClass('animate-pulse');
    });
  });

  describe('Transactions Display', () => {
    const mockTransactions = [
      createMockTransaction({
        id: 'trans-1',
        description: 'Coffee Shop',
        amountCents: -450,
        is_income: false,
        isNew: true,
      }),
      createMockTransaction({
        id: 'trans-2',
        description: 'Salary Deposit',
        amountCents: 300000,
        is_income: true,
        isNew: false,
      }),
    ];

    it('should display transaction list with proper formatting', () => {
      render(<RealtimeTransactionFeed transactions={mockTransactions} newCount={1} />);

      // Check transaction descriptions
      expect(screen.getByText('Coffee Shop')).toBeInTheDocument();
      expect(screen.getByText('Salary Deposit')).toBeInTheDocument();

      // Check formatted amounts
      expect(screen.getByText('-$4.50')).toBeInTheDocument();
      expect(screen.getByText('+$3,000.00')).toBeInTheDocument();

      // Check categories
      expect(screen.getAllByText('Food & Dining')).toHaveLength(2); // Both transactions have this category
      expect(screen.getAllByText('🍕')).toHaveLength(2); // Both have emoji

      // Check merchants
      expect(screen.getAllByText('Coffee Corner')).toHaveLength(2);

      // Check accounts
      expect(screen.getAllByText('Checking Account')).toHaveLength(2);

      // Check relative timestamps
      expect(screen.getAllByText('2 minutes ago')).toHaveLength(2);
    });

    it('should display new count badge when there are new transactions', () => {
      render(<RealtimeTransactionFeed transactions={mockTransactions} newCount={1} />);

      expect(screen.getByText('1 new')).toBeInTheDocument();
    });

    it('should not display new count badge when newCount is 0', () => {
      render(<RealtimeTransactionFeed transactions={mockTransactions} newCount={0} />);

      expect(screen.queryByText('1 new')).not.toBeInTheDocument();
    });

    it('should highlight new transactions', () => {
      render(<RealtimeTransactionFeed transactions={mockTransactions} newCount={1} />);

      // The first transaction is marked as new and should have special styling
      const newTransactionElement = screen.getByText('Coffee Shop').closest('div');
      expect(newTransactionElement).toHaveClass('bg-blue-50');
    });

    it('should display proper icons for income vs expense transactions', () => {
      render(<RealtimeTransactionFeed transactions={mockTransactions} newCount={1} />);

      // Income transactions should have green styling
      const salaryTransaction = screen.getByText('Salary Deposit').closest('div');
      expect(salaryTransaction?.querySelector('.bg-green-100')).toBeInTheDocument();

      // Expense transactions should have red styling
      const coffeeTransaction = screen.getByText('Coffee Shop').closest('div');
      expect(coffeeTransaction?.querySelector('.bg-red-100')).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    const mockTransactions = [
      createMockTransaction({ id: 'trans-1', isNew: true }),
      createMockTransaction({ id: 'trans-2', isNew: false }),
    ];

    it('should call markTransactionsSeen when Mark Seen button is clicked', () => {
      render(<RealtimeTransactionFeed transactions={mockTransactions} newCount={1} />);

      const markSeenButton = screen.getByText('Mark Seen');
      fireEvent.click(markSeenButton);

      expect(mockMarkTransactionsSeen).toHaveBeenCalledTimes(1);
    });

    it('should display Mark Seen button only when there are new transactions', () => {
      // With new transactions
      const { rerender } = render(<RealtimeTransactionFeed transactions={mockTransactions} newCount={1} />);
      expect(screen.getByText('Mark Seen')).toBeInTheDocument();

      // Without new transactions
      rerender(<RealtimeTransactionFeed transactions={mockTransactions} newCount={0} />);
      expect(screen.queryByText('Mark Seen')).not.toBeInTheDocument();
    });

    it('should call clearOldTransactions when Clear Old button is clicked', () => {
      // Create more than 20 transactions to trigger Clear Old button
      const manyTransactions = Array.from({ length: 25 }, (_, i) =>
        createMockTransaction({ id: `trans-${i}`, description: `Transaction ${i}` })
      );

      render(<RealtimeTransactionFeed transactions={manyTransactions} newCount={0} />);

      const clearOldButton = screen.getByText('Clear Old');
      fireEvent.click(clearOldButton);

      expect(mockClearOldTransactions).toHaveBeenCalledWith(20);
    });

    it('should display Clear Old button only when there are more than 20 transactions', () => {
      // With 20 or fewer transactions
      const fewTransactions = Array.from({ length: 20 }, (_, i) =>
        createMockTransaction({ id: `trans-${i}` })
      );
      const { rerender } = render(<RealtimeTransactionFeed transactions={fewTransactions} newCount={0} />);
      expect(screen.queryByText('Clear Old')).not.toBeInTheDocument();

      // With more than 20 transactions
      const manyTransactions = Array.from({ length: 25 }, (_, i) =>
        createMockTransaction({ id: `trans-${i}` })
      );
      rerender(<RealtimeTransactionFeed transactions={manyTransactions} newCount={0} />);
      expect(screen.getByText('Clear Old')).toBeInTheDocument();
    });
  });

  describe('Live Indicator', () => {
    it('should always display live indicator', () => {
      render(<RealtimeTransactionFeed transactions={[]} newCount={0} />);

      const liveText = screen.getByText('Live');
      expect(liveText).toBeInTheDocument();
      expect(liveText).toHaveClass('text-green-600');

      // Check for animated pulse indicator
      const pulseIndicator = liveText.previousSibling;
      expect(pulseIndicator).toHaveClass('animate-pulse');
      expect(pulseIndicator).toHaveClass('bg-green-500');
    });
  });

  describe('New Transaction Badge', () => {
    it('should display new badge for new transactions', () => {
      const newTransaction = createMockTransaction({ isNew: true });
      render(<RealtimeTransactionFeed transactions={[newTransaction]} newCount={1} />);

      expect(screen.getByText('New')).toBeInTheDocument();
    });

    it('should not display new badge for seen transactions', () => {
      const seenTransaction = createMockTransaction({ isNew: false });
      render(<RealtimeTransactionFeed transactions={[seenTransaction]} newCount={0} />);

      expect(screen.queryByText('New')).not.toBeInTheDocument();
    });
  });

  describe('Scrollable Container', () => {
    it('should have scrollable container with max height', () => {
      const manyTransactions = Array.from({ length: 10 }, (_, i) =>
        createMockTransaction({ id: `trans-${i}`, description: `Transaction ${i}` })
      );

      render(<RealtimeTransactionFeed transactions={manyTransactions} newCount={0} />);

      const scrollContainer = screen.getByText('Transaction 0').closest('.max-h-96');
      expect(scrollContainer).toBeInTheDocument();
      expect(scrollContainer).toHaveClass('overflow-y-auto');
    });
  });
});