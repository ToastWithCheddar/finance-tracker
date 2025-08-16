import { render, screen, fireEvent, waitFor } from '../../__tests__/utils/testUtils';
import userEvent from '@testing-library/user-event';
import { Budgets } from '../Budgets';
import { useBudgets, useBudgetSummary, useBudgetAlerts, useBudgetActions } from '../../hooks/useBudgets';
import { createMockBudget } from '../../__tests__/utils/mockFactories';

// Mock the hooks
jest.mock('../../hooks/useBudgets');

const mockUseBudgets = useBudgets as jest.MockedFunction<typeof useBudgets>;
const mockUseBudgetSummary = useBudgetSummary as jest.MockedFunction<typeof useBudgetSummary>;
const mockUseBudgetAlerts = useBudgetAlerts as jest.MockedFunction<typeof useBudgetAlerts>;
const mockUseBudgetActions = useBudgetActions as jest.MockedFunction<typeof useBudgetActions>;

// Mock BudgetCard and BudgetForm components
jest.mock('../../components/budgets/BudgetCard', () => ({
  BudgetCard: ({ budget, onEdit, onDelete }: any) => (
    <div data-testid={`budget-card-${budget.id}`}>
      <span>{budget.name}</span>
      <button onClick={() => onEdit(budget)}>Edit</button>
      <button onClick={() => onDelete(budget.id)}>Delete</button>
    </div>
  ),
}));

jest.mock('../../components/budgets/BudgetForm', () => ({
  BudgetForm: ({ isOpen, onClose, onSubmit, budget }: any) => (
    isOpen ? (
      <div data-testid="budget-form">
        <span>{budget ? 'Edit Budget' : 'New Budget'}</span>
        <button onClick={() => onSubmit({ name: 'Test Budget' })}>Submit</button>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null
  ),
}));

// Mock budgetService
jest.mock('../../services/budgetService', () => ({
  budgetService: {
    formatCurrency: (cents: number) => `$${(cents / 100).toFixed(2)}`,
    getPeriodDisplayName: (period: string) => period.charAt(0).toUpperCase() + period.slice(1),
  },
}));

describe('Budgets', () => {
  const mockCreate = jest.fn();
  const mockUpdate = jest.fn();
  const mockDelete = jest.fn();

  const mockBudgetData = {
    budgets: [
      createMockBudget({ id: 'budget-1', name: 'Food Budget', spent: 300.00, amount: 500.00 }),
      createMockBudget({ id: 'budget-2', name: 'Transport Budget', spent: 150.00, amount: 200.00 }),
    ],
    pagination: { page: 1, limit: 10, total: 2, totalPages: 1 },
  };

  const mockSummary = {
    total_budgets: 2,
    total_budgeted_cents: 70000,
    total_spent_cents: 45000,
    over_budget_count: 1,
  };

  const mockAlerts = [
    {
      budget_id: 'budget-1',
      budget_name: 'Food Budget',
      category_name: 'Food & Dining',
      alert_type: 'warning' as const,
      message: 'You have spent 80% of your budget',
    },
  ];

  beforeEach(() => {
    mockUseBudgets.mockReturnValue({
      data: mockBudgetData,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    mockUseBudgetSummary.mockReturnValue({
      data: mockSummary,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    mockUseBudgetAlerts.mockReturnValue({
      data: mockAlerts,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    mockUseBudgetActions.mockReturnValue({
      create: mockCreate,
      update: mockUpdate,
      delete: mockDelete,
      isCreating: false,
      isUpdating: false,
      isDeleting: false,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Page Header', () => {
    it('should display page title and description', () => {
      render(<Budgets />);
      
      expect(screen.getByText('Budget Management')).toBeInTheDocument();
      expect(screen.getByText('Track and manage your spending budgets')).toBeInTheDocument();
    });

    it('should display New Budget button', () => {
      render(<Budgets />);
      
      expect(screen.getByText('New Budget')).toBeInTheDocument();
    });

    it('should display Filters button', () => {
      render(<Budgets />);
      
      expect(screen.getByText('Filters')).toBeInTheDocument();
    });
  });

  describe('Summary Cards', () => {
    it('should display summary statistics', () => {
      render(<Budgets />);
      
      expect(screen.getByText('Total Budgets')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      
      expect(screen.getByText('Total Budgeted')).toBeInTheDocument();
      expect(screen.getByText('$700.00')).toBeInTheDocument();
      
      expect(screen.getByText('Total Spent')).toBeInTheDocument();
      expect(screen.getByText('$450.00')).toBeInTheDocument();
      
      expect(screen.getByText('Over Budget')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
    });
  });

  describe('Budget Alerts', () => {
    it('should display budget alerts when present', () => {
      render(<Budgets />);
      
      expect(screen.getByText('Budget Alerts')).toBeInTheDocument();
      expect(screen.getByText('Food Budget (Food & Dining)')).toBeInTheDocument();
      expect(screen.getByText('You have spent 80% of your budget')).toBeInTheDocument();
    });

    it('should not display alerts section when no alerts', () => {
      mockUseBudgetAlerts.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<Budgets />);
      
      expect(screen.queryByText('Budget Alerts')).not.toBeInTheDocument();
    });
  });

  describe('Budget List', () => {
    it('should display budget cards', () => {
      render(<Budgets />);
      
      expect(screen.getByTestId('budget-card-budget-1')).toBeInTheDocument();
      expect(screen.getByTestId('budget-card-budget-2')).toBeInTheDocument();
      expect(screen.getByText('Food Budget')).toBeInTheDocument();
      expect(screen.getByText('Transport Budget')).toBeInTheDocument();
    });

    it('should display empty state when no budgets', () => {
      mockUseBudgets.mockReturnValue({
        data: { budgets: [], pagination: { page: 1, limit: 10, total: 0, totalPages: 1 } },
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<Budgets />);
      
      expect(screen.getByText('No budgets yet')).toBeInTheDocument();
      expect(screen.getByText('Create your first budget to start tracking your spending.')).toBeInTheDocument();
      expect(screen.getByText('Create Your First Budget')).toBeInTheDocument();
    });
  });

  describe('Filtering Functionality', () => {
    const user = userEvent.setup();

    it('should show/hide filters when filter button is clicked', async () => {
      render(<Budgets />);
      
      const filtersButton = screen.getByText('Filters');
      
      // Initially filters should be hidden
      expect(screen.queryByText('Filter Budgets')).not.toBeInTheDocument();
      
      // Click to show filters
      await user.click(filtersButton);
      expect(screen.getByText('Filter Budgets')).toBeInTheDocument();
      
      // Click again to hide filters
      await user.click(filtersButton);
      expect(screen.queryByText('Filter Budgets')).not.toBeInTheDocument();
    });

    it('should call useBudgets with updated filters when period filter changes', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      // Show filters
      await user.click(screen.getByText('Filters'));
      
      // Change period filter
      const periodSelect = screen.getByDisplayValue('All Periods');
      await user.selectOptions(periodSelect, 'monthly');
      
      await waitFor(() => {
        expect(mockUseBudgets).toHaveBeenCalledWith({ period: 'monthly' });
      });
    });

    it('should call useBudgets with updated filters when status filter changes', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      // Show filters
      await user.click(screen.getByText('Filters'));
      
      // Change status filter
      const statusSelect = screen.getByDisplayValue('All Status');
      await user.selectOptions(statusSelect, 'true');
      
      await waitFor(() => {
        expect(mockUseBudgets).toHaveBeenCalledWith({ is_active: true });
      });
    });

    it('should call useBudgets with updated filters when budget status filter changes', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      // Show filters
      await user.click(screen.getByText('Filters'));
      
      // Change budget status filter
      const budgetStatusSelect = screen.getByDisplayValue('All Budgets');
      await user.selectOptions(budgetStatusSelect, 'true');
      
      await waitFor(() => {
        expect(mockUseBudgets).toHaveBeenCalledWith({ over_budget: true });
      });
    });

    it('should clear all filters when Clear Filters button is clicked', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      // Show filters
      await user.click(screen.getByText('Filters'));
      
      // Set some filters first
      const periodSelect = screen.getByDisplayValue('All Periods');
      await user.selectOptions(periodSelect, 'monthly');
      
      // Clear filters
      const clearButton = screen.getByText('Clear Filters');
      await user.click(clearButton);
      
      await waitFor(() => {
        expect(mockUseBudgets).toHaveBeenCalledWith({});
      });
    });

    it('should display filter indicator when filters are active', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      // Show filters
      await user.click(screen.getByText('Filters'));
      
      // Set a filter
      const periodSelect = screen.getByDisplayValue('All Periods');
      await user.selectOptions(periodSelect, 'monthly');
      
      // Filter indicator should be visible
      const filtersButton = screen.getByText('Filters');
      const indicator = filtersButton.parentElement?.querySelector('.bg-primary-600');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('Budget Actions', () => {
    const user = userEvent.setup();

    it('should open form for creating new budget when New Budget button is clicked', async () => {
      render(<Budgets />);
      
      const newBudgetButton = screen.getByText('New Budget');
      await user.click(newBudgetButton);
      
      expect(screen.getByTestId('budget-form')).toBeInTheDocument();
      expect(screen.getByText('New Budget')).toBeInTheDocument();
    });

    it('should open form for editing budget when Edit button is clicked', async () => {
      render(<Budgets />);
      
      const editButton = screen.getAllByText('Edit')[0];
      await user.click(editButton);
      
      expect(screen.getByTestId('budget-form')).toBeInTheDocument();
      expect(screen.getByText('Edit Budget')).toBeInTheDocument();
    });

    it('should call create mutation when form is submitted for new budget', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      // Open new budget form
      await user.click(screen.getByText('New Budget'));
      
      // Submit form
      await user.click(screen.getByText('Submit'));
      
      expect(mockCreate).toHaveBeenCalledWith(
        { name: 'Test Budget' },
        expect.objectContaining({
          onSuccess: expect.any(Function),
        })
      );
    });

    it('should call update mutation when form is submitted for existing budget', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      // Open edit form
      await user.click(screen.getAllByText('Edit')[0]);
      
      // Submit form
      await user.click(screen.getByText('Submit'));
      
      expect(mockUpdate).toHaveBeenCalledWith(
        { budgetId: 'budget-1', budget: { name: 'Test Budget' } },
        expect.objectContaining({
          onSuccess: expect.any(Function),
        })
      );
    });

    it('should call delete mutation when delete button is clicked', async () => {
      const user = userEvent.setup();
      render(<Budgets />);
      
      const deleteButton = screen.getAllByText('Delete')[0];
      await user.click(deleteButton);
      
      expect(mockDelete).toHaveBeenCalledWith('budget-1');
    });
  });

  describe('Loading States', () => {
    it('should display loading spinner when data is loading', () => {
      mockUseBudgets.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(<Budgets />);
      
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

  describe('Error States', () => {
    it('should display error message when budgets fail to load', () => {
      mockUseBudgets.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: jest.fn(),
      });

      render(<Budgets />);
      
      expect(screen.getByText('Failed to load budgets. Please try refreshing the page.')).toBeInTheDocument();
    });
  });
});