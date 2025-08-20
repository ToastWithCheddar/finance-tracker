import { render, screen, fireEvent, waitFor } from '../../../__tests__/utils/testUtils';
import userEvent from '@testing-library/user-event';
import { BudgetCard } from '../BudgetCard';
import { createMockBudget } from '../../../__tests__/utils/mockFactories';

// Mock budgetService
const mockBudgetService = {
  getBudgetStatus: jest.fn(),
  getBudgetStatusColor: jest.fn(),
  getBudgetStatusBgColor: jest.fn(),
  getPeriodDisplayName: jest.fn(),
  formatCurrency: jest.fn(),
  calculateDaysRemaining: jest.fn(),
  formatPercentage: jest.fn(),
};

jest.mock('../../../services/budgetService', () => ({
  budgetService: mockBudgetService,
}));

describe('BudgetCard', () => {
  const mockOnEdit = jest.fn();
  const mockOnDelete = jest.fn();

  const defaultBudget = createMockBudget({
    id: 'budget-1',
    name: 'Food Budget',
    amount_cents: 50000, // $500.00
    period: 'monthly',
    category_name: 'Food & Dining',
    usage: {
      spent_cents: 30000, // $300.00
      remaining_cents: 20000, // $200.00
      percentage_used: 60,
      is_over_budget: false,
    },
  });

  beforeEach(() => {
    // Setup default mock returns
    mockBudgetService.getBudgetStatus.mockReturnValue('on-track');
    mockBudgetService.getBudgetStatusColor.mockReturnValue('text-green-600');
    mockBudgetService.getBudgetStatusBgColor.mockReturnValue('bg-green-100');
    mockBudgetService.getPeriodDisplayName.mockReturnValue('Monthly');
    mockBudgetService.formatCurrency.mockImplementation((cents: number) => `$${(cents / 100).toFixed(2)}`);
    mockBudgetService.calculateDaysRemaining.mockReturnValue('15 days remaining');
    mockBudgetService.formatPercentage.mockImplementation((percentage: number) => `${percentage}%`);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render budget name and category', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.getByText('Food Budget')).toBeInTheDocument();
      expect(screen.getByText('Category: Food & Dining')).toBeInTheDocument();
    });

    it('should render budget amount and period', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.getByText('$500.00')).toBeInTheDocument();
      expect(screen.getByText('Monthly')).toBeInTheDocument();
      expect(mockBudgetService.getPeriodDisplayName).toHaveBeenCalledWith('monthly');
    });

    it('should render budget status badge', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.getByText('on track')).toBeInTheDocument();
      expect(mockBudgetService.getBudgetStatus).toHaveBeenCalledWith(defaultBudget.usage);
    });

    it('should render days remaining', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.getByText('15 days remaining')).toBeInTheDocument();
      expect(mockBudgetService.calculateDaysRemaining).toHaveBeenCalledWith(defaultBudget.usage);
    });
  });

  describe('Progress Bar', () => {
    it('should render progress bar with correct percentage', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.getByText('Progress')).toBeInTheDocument();
      expect(screen.getByText('60%')).toBeInTheDocument();
      
      const progressBar = screen.getByText('Progress').closest('.mb-4')?.querySelector('.h-2');
      expect(progressBar).toHaveStyle({ width: '60%' });
    });

    it('should render green progress bar for on-track budget', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const progressBar = screen.getByText('Progress').closest('.mb-4')?.querySelector('.h-2');
      expect(progressBar).toHaveClass('bg-green-500');
    });

    it('should render yellow progress bar for near-limit budget', () => {
      const nearLimitBudget = createMockBudget({
        ...defaultBudget,
        usage: {
          ...defaultBudget.usage!,
          percentage_used: 85,
        },
      });

      render(<BudgetCard budget={nearLimitBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const progressBar = screen.getByText('Progress').closest('.mb-4')?.querySelector('.h-2');
      expect(progressBar).toHaveClass('bg-yellow-500');
    });

    it('should render red progress bar for over-budget', () => {
      const overBudget = createMockBudget({
        ...defaultBudget,
        usage: {
          spent_cents: 60000,
          remaining_cents: -10000,
          percentage_used: 120,
          is_over_budget: true,
        },
      });

      render(<BudgetCard budget={overBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const progressBar = screen.getByText('Progress').closest('.mb-4')?.querySelector('.h-2');
      expect(progressBar).toHaveClass('bg-red-500');
    });

    it('should cap progress bar width at 100%', () => {
      const overBudget = createMockBudget({
        ...defaultBudget,
        usage: {
          ...defaultBudget.usage!,
          percentage_used: 150,
        },
      });

      render(<BudgetCard budget={overBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const progressBar = screen.getByText('Progress').closest('.mb-4')?.querySelector('.h-2');
      expect(progressBar).toHaveStyle({ width: '100%' });
    });
  });

  describe('Spending Details', () => {
    it('should render spent and remaining amounts', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.getByText('Spent')).toBeInTheDocument();
      expect(screen.getByText('$300.00')).toBeInTheDocument();
      
      expect(screen.getByText('Remaining')).toBeInTheDocument();
      expect(screen.getByText('$200.00')).toBeInTheDocument();
    });

    it('should render negative remaining amount in red', () => {
      const overBudget = createMockBudget({
        ...defaultBudget,
        usage: {
          spent_cents: 60000,
          remaining_cents: -10000,
          percentage_used: 120,
          is_over_budget: true,
        },
      });

      render(<BudgetCard budget={overBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const remainingAmount = screen.getByText('-$100.00');
      expect(remainingAmount).toHaveClass('text-red-600');
    });

    it('should render positive remaining amount in green', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const remainingAmount = screen.getByText('$200.00');
      expect(remainingAmount).toHaveClass('text-green-600');
    });
  });

  describe('Over Budget Warning', () => {
    it('should display warning when over budget', () => {
      const overBudget = createMockBudget({
        ...defaultBudget,
        usage: {
          spent_cents: 60000,
          remaining_cents: -10000,
          percentage_used: 120,
          is_over_budget: true,
        },
      });

      render(<BudgetCard budget={overBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.getByText(/Over budget by/)).toBeInTheDocument();
      expect(screen.getByText('$100.00')).toBeInTheDocument();
    });

    it('should not display warning when within budget', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.queryByText(/Over budget by/)).not.toBeInTheDocument();
    });

    it('should display alert icon when over budget', () => {
      const overBudget = createMockBudget({
        ...defaultBudget,
        usage: {
          ...defaultBudget.usage!,
          is_over_budget: true,
        },
      });

      render(<BudgetCard budget={overBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const alertIcons = screen.getAllByRole('img', { hidden: true });
      expect(alertIcons.length).toBeGreaterThan(0);
    });
  });

  describe('User Interactions', () => {
    const user = userEvent.setup();

    it('should call onEdit when edit button is clicked', async () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const editButton = screen.getByRole('button', { name: /edit/i });
      await user.click(editButton);
      
      expect(mockOnEdit).toHaveBeenCalledWith(defaultBudget);
    });

    it('should show delete confirmation modal when delete button is clicked', async () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const deleteButton = screen.getByRole('button', { name: /delete budget/i });
      await user.click(deleteButton);
      
      expect(screen.getByText('Delete Budget')).toBeInTheDocument();
      expect(screen.getByText('This action cannot be undone')).toBeInTheDocument();
      expect(screen.getByText(/Are you sure you want to delete the budget "Food Budget"/)).toBeInTheDocument();
    });

    it('should cancel delete confirmation when cancel button is clicked', async () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const deleteButton = screen.getByRole('button', { name: /delete budget/i });
      await user.click(deleteButton);
      
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);
      
      expect(screen.queryByText('Delete Budget')).not.toBeInTheDocument();
    });

    it('should call onDelete when confirm delete button is clicked', async () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const deleteButton = screen.getByRole('button', { name: /delete budget/i });
      await user.click(deleteButton);
      
      const confirmButton = screen.getByRole('button', { name: /delete budget/i });
      await user.click(confirmButton);
      
      expect(mockOnDelete).toHaveBeenCalledWith('budget-1');
    });

    it('should open alert settings modal when alert settings button is clicked', async () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const alertSettingsButton = screen.getByRole('button', { name: /alert settings/i });
      await user.click(alertSettingsButton);
      
      await waitFor(() => {
        expect(screen.getByText('Alert Settings')).toBeInTheDocument();
      });
    });

    it('should open calendar modal when calendar button is clicked', async () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const calendarButton = screen.getByRole('button', { name: /calendar view/i });
      await user.click(calendarButton);
      
      await waitFor(() => {
        expect(screen.getByText('Budget Calendar')).toBeInTheDocument();
      });
    });

    it('should disable buttons when loading', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} isLoading={true} />);
      
      const editButton = screen.getByRole('button', { name: /edit budget/i });
      const deleteButton = screen.getByRole('button', { name: /delete budget/i });
      const calendarButton = screen.getByRole('button', { name: /calendar view/i });
      const alertButton = screen.getByRole('button', { name: /alert settings/i });
      
      expect(editButton).toBeDisabled();
      expect(deleteButton).toBeDisabled();
      expect(calendarButton).toBeDisabled();
      expect(alertButton).toBeDisabled();
    });

    it('should apply opacity when loading', () => {
      render(<BudgetCard budget={defaultBudget} onEdit={mockOnEdit} onDelete={mockOnDelete} isLoading={true} />);
      
      const card = screen.getByText('Food Budget').closest('.opacity-50');
      expect(card).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should render without category name', () => {
      const budgetWithoutCategory = createMockBudget({
        ...defaultBudget,
        category_name: undefined,
      });

      render(<BudgetCard budget={budgetWithoutCategory} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.queryByText(/Category:/)).not.toBeInTheDocument();
    });

    it('should render without usage data', () => {
      const budgetWithoutUsage = createMockBudget({
        ...defaultBudget,
        usage: undefined,
      });

      render(<BudgetCard budget={budgetWithoutUsage} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      expect(screen.queryByText('Progress')).not.toBeInTheDocument();
      expect(screen.queryByText('Spent')).not.toBeInTheDocument();
      expect(screen.queryByText('Remaining')).not.toBeInTheDocument();
    });

    it('should handle zero percentage used', () => {
      const budgetZeroUsage = createMockBudget({
        ...defaultBudget,
        usage: {
          ...defaultBudget.usage!,
          percentage_used: 0,
        },
      });

      render(<BudgetCard budget={budgetZeroUsage} onEdit={mockOnEdit} onDelete={mockOnDelete} />);
      
      const progressBar = screen.getByText('Progress').closest('.mb-4')?.querySelector('.h-2');
      expect(progressBar).toHaveStyle({ width: '0%' });
    });
  });
});