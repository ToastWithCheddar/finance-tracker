import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Transactions } from '../Transactions';
import { renderWithProviders } from '../../__tests__/utils/testUtils';
import * as transactionHooks from '../../hooks/useTransactions';

// Mock the transaction hooks
vi.mock('../../hooks/useTransactions');

const mockTransactions = [
  {
    id: 1,
    description: 'Grocery shopping',
    amount: -85.32,
    transaction_date: '2023-10-15',
    category: 'Groceries',
    categoryId: 'cat1',
    transaction_type: 'expense',
  },
  {
    id: 2,
    description: 'Salary payment',
    amount: 3000.00,
    transaction_date: '2023-10-01',
    category: 'Salary',
    categoryId: 'cat2',
    transaction_type: 'income',
  },
  {
    id: 3,
    description: 'Coffee shop',
    amount: -4.50,
    transaction_date: '2023-10-14',
    category: 'Food & Dining',
    categoryId: 'cat3',
    transaction_type: 'expense',
  },
];

const mockTransactionData = {
  items: mockTransactions,
  total: 150,
  page: 1,
  pages: 6,
  per_page: 25,
};

const mockStats = {
  total_income: 3000.00,
  total_expenses: 89.82,
  net_amount: 2910.18,
  transaction_count: 3,
};

const mockTransactionActions = {
  create: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
  bulkDelete: vi.fn(),
  importCSV: vi.fn(),
  export: vi.fn(),
  isCreating: false,
  isUpdating: false,
  isDeleting: false,
  isBulkDeleting: false,
  isImporting: false,
  isExporting: false,
};

describe('Transactions Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock useTransactions hook
    vi.mocked(transactionHooks.useTransactions).mockReturnValue({
      data: mockTransactionData,
      isLoading: false,
      error: null,
    } as any);
    
    // Mock useTransactionStats hook
    vi.mocked(transactionHooks.useTransactionStats).mockReturnValue({
      data: mockStats,
      isLoading: false,
      error: null,
    } as any);
    
    // Mock useTransactionActions hook
    vi.mocked(transactionHooks.useTransactionActions).mockReturnValue(mockTransactionActions);
  });

  describe('Page Loading and Rendering', () => {
    it('renders the transactions page with header and transactions', async () => {
      renderWithProviders(<Transactions />);
      
      expect(screen.getByText('Transactions')).toBeInTheDocument();
      expect(screen.getByText('Manage your income and expenses')).toBeInTheDocument();
      
      // Check if transactions are rendered
      await waitFor(() => {
        expect(screen.getByText('Grocery shopping')).toBeInTheDocument();
        expect(screen.getByText('Salary payment')).toBeInTheDocument();
        expect(screen.getByText('Coffee shop')).toBeInTheDocument();
      });
    });

    it('displays loading state when data is loading', () => {
      vi.mocked(transactionHooks.useTransactions).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as any);

      renderWithProviders(<Transactions />);
      
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('displays error state when there is an error', () => {
      vi.mocked(transactionHooks.useTransactions).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('API Error'),
      } as any);

      renderWithProviders(<Transactions />);
      
      expect(screen.getByText('Failed to load transactions')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('displays empty state when no transactions exist', () => {
      vi.mocked(transactionHooks.useTransactions).mockReturnValue({
        data: { items: [], total: 0, page: 1, pages: 1, per_page: 25 },
        isLoading: false,
        error: null,
      } as any);

      renderWithProviders(<Transactions />);
      
      expect(screen.getByText('No transactions found')).toBeInTheDocument();
      expect(screen.getByText('Start by adding your first transaction or adjust your filters.')).toBeInTheDocument();
    });
  });

  describe('Filtering Functionality', () => {
    it('updates search filter when user types in search box', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      const searchInput = screen.getByPlaceholderText('Search transactions...');
      await user.type(searchInput, 'grocery');
      
      expect(searchInput).toHaveValue('grocery');
      
      // Should trigger useTransactions with the search filter
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'grocery',
            page: 1,
            per_page: 25,
          })
        );
      });
    });

    it('expands filter panel when Filters button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      const filtersButton = screen.getByRole('button', { name: /filters/i });
      await user.click(filtersButton);
      
      // Advanced filters should now be visible
      expect(screen.getByLabelText('Start Date')).toBeInTheDocument();
      expect(screen.getByLabelText('End Date')).toBeInTheDocument();
      expect(screen.getByLabelText('Transaction Type')).toBeInTheDocument();
    });

    it('applies date range filters correctly', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Expand filters
      const filtersButton = screen.getByRole('button', { name: /filters/i });
      await user.click(filtersButton);
      
      // Set date range
      const startDateInput = screen.getByLabelText('Start Date');
      const endDateInput = screen.getByLabelText('End Date');
      
      await user.type(startDateInput, '2023-10-01');
      await user.type(endDateInput, '2023-10-15');
      
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            dateFrom: '2023-10-01',
            dateTo: '2023-10-15',
            page: 1,
            per_page: 25,
          })
        );
      });
    });

    it('applies transaction type filter correctly', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Expand filters
      const filtersButton = screen.getByRole('button', { name: /filters/i });
      await user.click(filtersButton);
      
      // Select expense type
      const typeSelect = screen.getByDisplayValue('All Types');
      await user.selectOptions(typeSelect, 'expense');
      
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            transaction_type: 'expense',
            page: 1,
            per_page: 25,
          })
        );
      });
    });

    it('uses quick filter buttons', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Expand filters
      const filtersButton = screen.getByRole('button', { name: /filters/i });
      await user.click(filtersButton);
      
      // Click "This Month" quick filter
      const thisMonthButton = screen.getByRole('button', { name: 'This Month' });
      await user.click(thisMonthButton);
      
      // Should update the date inputs
      const today = new Date();
      const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
      const expectedStartDate = startOfMonth.toISOString().split('T')[0];
      const expectedEndDate = today.toISOString().split('T')[0];
      
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            dateFrom: expectedStartDate,
            dateTo: expectedEndDate,
            page: 1,
            per_page: 25,
          })
        );
      });
    });

    it('clears all filters when Clear All button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // First set a search filter
      const searchInput = screen.getByPlaceholderText('Search transactions...');
      await user.type(searchInput, 'grocery');
      
      // Clear all filters
      const clearButton = screen.getByRole('button', { name: 'Clear All' });
      await user.click(clearButton);
      
      expect(searchInput).toHaveValue('');
      
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            page: 1,
            per_page: 25,
          })
        );
      });
    });
  });

  describe('Pagination Functionality', () => {
    it('displays pagination controls when there are multiple pages', () => {
      renderWithProviders(<Transactions />);
      
      expect(screen.getByText('Showing 1 to 3 of 150 transactions')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Previous' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Next' })).toBeInTheDocument();
      
      // Should show page numbers
      expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument();
    });

    it('navigates to next page when Next button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      const nextButton = screen.getByRole('button', { name: 'Next' });
      await user.click(nextButton);
      
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            page: 2,
            per_page: 25,
          })
        );
      });
    });

    it('navigates to specific page when page number is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      const pageButton = screen.getByRole('button', { name: '3' });
      await user.click(pageButton);
      
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            page: 3,
            per_page: 25,
          })
        );
      });
    });

    it('disables Previous button on first page', () => {
      renderWithProviders(<Transactions />);
      
      const prevButton = screen.getByRole('button', { name: 'Previous' });
      expect(prevButton).toBeDisabled();
    });

    it('resets to page 1 when filters change', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Go to page 2 first
      const nextButton = screen.getByRole('button', { name: 'Next' });
      await user.click(nextButton);
      
      // Now change a filter
      const searchInput = screen.getByPlaceholderText('Search transactions...');
      await user.type(searchInput, 'grocery');
      
      // Should reset to page 1
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'grocery',
            page: 1,
            per_page: 25,
          })
        );
      });
    });
  });

  describe('Transaction Actions', () => {
    it('opens transaction form when Add Transaction button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      const addButton = screen.getByRole('button', { name: '➕ Add Transaction' });
      await user.click(addButton);
      
      // Transaction form modal should be open
      expect(screen.getByText('Add Transaction')).toBeInTheDocument();
    });

    it('opens CSV import modal when Import CSV button is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      const importButton = screen.getByRole('button', { name: '📥 Import CSV' });
      await user.click(importButton);
      
      // CSV import modal should be open (assuming it has identifiable content)
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('handles export button clicks', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      const exportButton = screen.getByRole('button', { name: '📤 Export' });
      await user.hover(exportButton);
      
      // Export dropdown should appear
      const csvExportButton = await screen.findByText('Export as CSV');
      await user.click(csvExportButton);
      
      expect(mockTransactionActions.export).toHaveBeenCalledWith(
        expect.objectContaining({
          format: 'csv',
        })
      );
    });

    it('handles transaction editing', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Find and click edit button for first transaction
      const editButtons = screen.getAllByText('✏️');
      await user.click(editButtons[0]);
      
      // Should open edit form
      expect(screen.getByText('Edit Transaction')).toBeInTheDocument();
    });

    it('handles transaction deletion with confirmation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Find and click delete button for first transaction
      const deleteButtons = screen.getAllByText('🗑️');
      await user.click(deleteButtons[0]);
      
      // Should show confirmation dialog
      expect(screen.getByText('Delete Transaction')).toBeInTheDocument();
      expect(screen.getByText('Are you sure you want to delete this transaction? This action cannot be undone.')).toBeInTheDocument();
      
      // Confirm deletion
      const confirmButton = screen.getByRole('button', { name: 'Delete' });
      await user.click(confirmButton);
      
      expect(mockTransactionActions.delete).toHaveBeenCalledWith('1');
    });

    it('handles bulk selection and deletion', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Select all transactions
      const selectAllCheckbox = screen.getByRole('checkbox', { name: /select all/i });
      await user.click(selectAllCheckbox);
      
      // Should show bulk delete button
      const bulkDeleteButton = screen.getByRole('button', { name: /delete selected \(3\)/i });
      expect(bulkDeleteButton).toBeInTheDocument();
      
      await user.click(bulkDeleteButton);
      
      expect(mockTransactionActions.bulkDelete).toHaveBeenCalledWith(['1', '2', '3']);
    });
  });

  describe('Statistics Display', () => {
    it('displays transaction statistics correctly', () => {
      renderWithProviders(<Transactions />);
      
      expect(screen.getByText('$3,000.00')).toBeInTheDocument(); // Total income
      expect(screen.getByText('$89.82')).toBeInTheDocument(); // Total expenses
      expect(screen.getByText('$2,910.18')).toBeInTheDocument(); // Net amount
      expect(screen.getByText('3')).toBeInTheDocument(); // Transaction count
      
      expect(screen.getByText('Total Income')).toBeInTheDocument();
      expect(screen.getByText('Total Expenses')).toBeInTheDocument();
      expect(screen.getByText('Net Amount')).toBeInTheDocument();
      expect(screen.getByText('Transactions')).toBeInTheDocument();
    });
  });

  describe('Transaction List Display', () => {
    it('displays transactions with correct formatting', () => {
      renderWithProviders(<Transactions />);
      
      // Check transaction content
      expect(screen.getByText('Grocery shopping')).toBeInTheDocument();
      expect(screen.getByText('Salary payment')).toBeInTheDocument();
      expect(screen.getByText('Coffee shop')).toBeInTheDocument();
      
      // Check amounts are formatted correctly
      expect(screen.getByText('-$85.32')).toBeInTheDocument();
      expect(screen.getByText('+$3,000.00')).toBeInTheDocument();
      expect(screen.getByText('-$4.50')).toBeInTheDocument();
      
      // Check transaction types are displayed
      expect(screen.getAllByText('expense')).toHaveLength(2);
      expect(screen.getByText('income')).toBeInTheDocument();
    });

    it('displays transaction categories and dates correctly', () => {
      renderWithProviders(<Transactions />);
      
      expect(screen.getByText('Groceries')).toBeInTheDocument();
      expect(screen.getByText('Salary')).toBeInTheDocument();
      expect(screen.getByText('Food & Dining')).toBeInTheDocument();
      
      // Dates should be formatted
      expect(screen.getByText('Oct 15, 2023')).toBeInTheDocument();
      expect(screen.getByText('Oct 1, 2023')).toBeInTheDocument();
      expect(screen.getByText('Oct 14, 2023')).toBeInTheDocument();
    });
  });

  describe('State Management', () => {
    it('tracks filter state correctly', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Apply multiple filters
      const searchInput = screen.getByPlaceholderText('Search transactions...');
      await user.type(searchInput, 'grocery');
      
      // Expand filters and set transaction type
      const filtersButton = screen.getByRole('button', { name: /filters/i });
      await user.click(filtersButton);
      
      const typeSelect = screen.getByDisplayValue('All Types');
      await user.selectOptions(typeSelect, 'expense');
      
      // Should call useTransactions with combined filters
      await waitFor(() => {
        expect(transactionHooks.useTransactions).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'grocery',
            transaction_type: 'expense',
            page: 1,
            per_page: 25,
          })
        );
      });
    });

    it('shows active filters with correct count', async () => {
      const user = userEvent.setup();
      renderWithProviders(<Transactions />);
      
      // Apply a search filter
      const searchInput = screen.getByPlaceholderText('Search transactions...');
      await user.type(searchInput, 'grocery');
      
      // Should show filter count badge
      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument(); // Filter count badge
        expect(screen.getByText('Search: "grocery"')).toBeInTheDocument(); // Active filter display
      });
    });
  });
});