import { render, screen, waitFor } from '../../__tests__/utils/testUtils';
import { Insights } from '../Insights';
import { useRealtimeStore } from '../../stores/realtimeStore';
import { api } from '../../services/api';

// Mock the API
jest.mock('../../services/api');
const mockApi = api as jest.Mocked<typeof api>;

// Mock the realtime store
jest.mock('../../stores/realtimeStore');
const mockUseRealtimeStore = useRealtimeStore as jest.MockedFunction<typeof useRealtimeStore>;

// Mock data
const mockHistoricalInsights = {
  insights: [
    {
      id: '1',
      type: 'spending_spike',
      title: 'Unusual spending in Coffee category',
      description: 'You\'ve spent $150 on Coffee this week, which is 40% higher than your average.',
      priority: 1,
      is_read: false,
      extra_payload: {
        amount_cents: 15000,
        action_items: ['Consider setting a budget for coffee expenses', 'Look for cheaper alternatives']
      },
      created_at: '2025-08-12T10:00:00Z',
      updated_at: '2025-08-12T10:00:00Z'
    },
    {
      id: '2',
      type: 'savings_opportunity',
      title: 'Savings opportunity detected',
      description: 'You could save $50 per month by canceling unused subscriptions.',
      priority: 2,
      is_read: true,
      extra_payload: {
        amount_cents: 5000,
        action_items: ['Review your subscription list']
      },
      created_at: '2025-08-11T09:00:00Z',
      updated_at: '2025-08-11T09:00:00Z'
    }
  ],
  total_count: 2,
  unread_count: 1
};

const mockRealtimeInsights = [
  {
    id: '3',
    type: 'goal_progress',
    title: 'Goal progress update',
    description: 'You\'re 75% towards your vacation savings goal!',
    priority: 3,
    is_read: false,
    extra_payload: {},
    created_at: '2025-08-12T11:00:00Z',
    isNew: true
  }
];

describe('Insights', () => {
  beforeEach(() => {
    // Mock the realtime store to return empty insights initially
    mockUseRealtimeStore.mockReturnValue({
      insights: []
    } as any);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should display loading spinner when data is loading', () => {
      // Mock API to never resolve (loading state)
      mockApi.get.mockReturnValue(new Promise(() => {}));

      render(<Insights />);

      expect(screen.getByText('AI Insights')).toBeInTheDocument();
      expect(screen.getByRole('status')).toBeInTheDocument(); // LoadingSpinner has role="status"
    });
  });

  describe('Error State', () => {
    it('should display error message when API fails', async () => {
      // Mock API to reject
      mockApi.get.mockRejectedValue(new Error('Failed to fetch insights'));

      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument();
        expect(screen.getByText(/Failed to load insights/)).toBeInTheDocument();
      });
    });
  });

  describe('Success State', () => {
    beforeEach(() => {
      // Mock successful API response
      mockApi.get.mockResolvedValue({
        data: mockHistoricalInsights
      });
    });

    it('should display insights summary cards', async () => {
      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('Total Insights')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument(); // total_count
        expect(screen.getByText('Unread')).toBeInTheDocument();
        expect(screen.getByText('1')).toBeInTheDocument(); // unread_count
        expect(screen.getByText('New Today')).toBeInTheDocument();
        expect(screen.getByText('0')).toBeInTheDocument(); // no realtime insights initially
      });
    });

    it('should display historical insights', async () => {
      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('Unusual spending in Coffee category')).toBeInTheDocument();
        expect(screen.getByText(/You've spent \$150 on Coffee this week/)).toBeInTheDocument();
        expect(screen.getByText('Savings opportunity detected')).toBeInTheDocument();
      });
    });

    it('should show unread indicator for unread insights', async () => {
      render(<Insights />);

      await waitFor(() => {
        const unreadInsight = screen.getByText('Unusual spending in Coffee category').closest('[class*="ring-2"]');
        expect(unreadInsight).toBeInTheDocument();
      });
    });

    it('should display action items when available', async () => {
      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('Recommended Actions:')).toBeInTheDocument();
        expect(screen.getByText('Consider setting a budget for coffee expenses')).toBeInTheDocument();
        expect(screen.getByText('Look for cheaper alternatives')).toBeInTheDocument();
      });
    });

    it('should display amount information when available', async () => {
      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText(/Amount: \$150\.00/)).toBeInTheDocument();
      });
    });

    it('should display proper insight type and timing', async () => {
      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('spending spike')).toBeInTheDocument();
        expect(screen.getByText(/Generated \d+ (hour|day)s? ago/)).toBeInTheDocument();
      });
    });
  });

  describe('Real-time Updates', () => {
    beforeEach(() => {
      // Mock successful API response
      mockApi.get.mockResolvedValue({
        data: mockHistoricalInsights
      });
    });

    it('should display real-time insights', async () => {
      // Mock realtime store with insights
      mockUseRealtimeStore.mockReturnValue({
        insights: mockRealtimeInsights
      } as any);

      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('Goal progress update')).toBeInTheDocument();
        expect(screen.getByText(/You're 75% towards your vacation savings goal/)).toBeInTheDocument();
      });
    });

    it('should update new today count with real-time insights', async () => {
      // Mock realtime store with insights
      mockUseRealtimeStore.mockReturnValue({
        insights: mockRealtimeInsights
      } as any);

      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('New Today')).toBeInTheDocument();
        expect(screen.getByText('1')).toBeInTheDocument(); // 1 realtime insight
      });
    });

    it('should merge historical and real-time insights without duplicates', async () => {
      // Mock realtime store with insights including a duplicate
      const realtimeWithDuplicate = [
        ...mockRealtimeInsights,
        { ...mockHistoricalInsights.insights[0], isNew: true } // duplicate from historical
      ];
      
      mockUseRealtimeStore.mockReturnValue({
        insights: realtimeWithDuplicate
      } as any);

      render(<Insights />);

      await waitFor(() => {
        // Should only see unique insights
        const coffeeInsights = screen.getAllByText('Unusual spending in Coffee category');
        expect(coffeeInsights).toHaveLength(1);
      });
    });
  });

  describe('Empty State', () => {
    it('should display empty state when no insights are available', async () => {
      // Mock API to return empty results
      mockApi.get.mockResolvedValue({
        data: {
          insights: [],
          total_count: 0,
          unread_count: 0
        }
      });

      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText(/No insights available yet/)).toBeInTheDocument();
        expect(screen.getByText(/Check back later for personalized financial recommendations/)).toBeInTheDocument();
      });
    });
  });

  describe('Insight Types and Icons', () => {
    beforeEach(() => {
      mockApi.get.mockResolvedValue({
        data: {
          insights: [
            {
              id: '1',
              type: 'spending_spike',
              title: 'Spending spike',
              description: 'Test',
              priority: 1,
              is_read: false,
              extra_payload: {},
              created_at: '2025-08-12T10:00:00Z'
            },
            {
              id: '2',
              type: 'savings_opportunity',
              title: 'Savings opportunity',
              description: 'Test',
              priority: 2,
              is_read: false,
              extra_payload: {},
              created_at: '2025-08-12T10:00:00Z'
            },
            {
              id: '3',
              type: 'budget_alert',
              title: 'Budget alert',
              description: 'Test',
              priority: 1,
              is_read: false,
              extra_payload: {},
              created_at: '2025-08-12T10:00:00Z'
            }
          ],
          total_count: 3,
          unread_count: 3
        }
      });
    });

    it('should display correct icons for different insight types', async () => {
      render(<Insights />);

      await waitFor(() => {
        expect(screen.getByText('Spending spike')).toBeInTheDocument();
        expect(screen.getByText('Savings opportunity')).toBeInTheDocument();
        expect(screen.getByText('Budget alert')).toBeInTheDocument();
      });
    });
  });

  describe('Priority Styling', () => {
    beforeEach(() => {
      mockApi.get.mockResolvedValue({
        data: {
          insights: [
            {
              id: '1',
              type: 'budget_alert',
              title: 'High Priority',
              description: 'Test',
              priority: 1, // High
              is_read: false,
              extra_payload: {},
              created_at: '2025-08-12T10:00:00Z'
            },
            {
              id: '2',
              type: 'spending_spike',
              title: 'Medium Priority',
              description: 'Test',
              priority: 2, // Medium
              is_read: false,
              extra_payload: {},
              created_at: '2025-08-12T10:00:00Z'
            },
            {
              id: '3',
              type: 'savings_opportunity',
              title: 'Low Priority',
              description: 'Test',
              priority: 3, // Low
              is_read: false,
              extra_payload: {},
              created_at: '2025-08-12T10:00:00Z'
            }
          ],
          total_count: 3,
          unread_count: 3
        }
      });
    });

    it('should apply correct color styling based on priority', async () => {
      render(<Insights />);

      await waitFor(() => {
        // High priority should have red styling
        const highPriorityCard = screen.getByText('High Priority').closest('[class*="text-red-600"]');
        expect(highPriorityCard).toBeInTheDocument();

        // Medium priority should have yellow styling
        const mediumPriorityCard = screen.getByText('Medium Priority').closest('[class*="text-yellow-600"]');
        expect(mediumPriorityCard).toBeInTheDocument();

        // Low priority should have blue styling
        const lowPriorityCard = screen.getByText('Low Priority').closest('[class*="text-blue-600"]');
        expect(lowPriorityCard).toBeInTheDocument();
      });
    });
  });
});