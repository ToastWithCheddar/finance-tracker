/**
 * TransactionList — renders rows and surfaces empty/loading states.
 *
 * TransactionItem pulls in `lucide-react` + mlService which aren't installed
 * in the audit workspace — we mock the child so this test focuses on
 * TransactionList's own logic.
 *
 * FE-PERF-003: virtualization is currently a TODO in the source (see the
 * react-window stub block in TransactionList.tsx). The skipped test below
 * pins that gap so it surfaces when `react-window` lands.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { Transaction } from '@/types/transaction';

// Mock children/utilities BEFORE importing the component.
vi.mock('@/components/transactions/TransactionItem', () => ({
  TransactionItem: ({ transaction }: { transaction: Transaction }) => (
    <div data-testid="tx-row">{transaction.description}</div>
  ),
}));

// Modal renders into a portal that touches happy-dom APIs we don't need —
// stub it to a passthrough so the closed delete-confirm modal just renders null.
vi.mock('@/components/ui/Modal', () => ({
  Modal: ({ isOpen, children }: any) => (isOpen ? <div>{children}</div> : null),
}));

const { TransactionList } = await import('@/components/transactions/TransactionList');

function makeTx(id: string, description: string): Transaction {
  return {
    id,
    userId: 'u-1',
    accountId: 'acct-1',
    categoryId: 'cat-1',
    amountCents: 1000,
    currency: 'USD',
    description,
    transactionDate: '2026-04-01',
    createdAt: '2026-04-01T00:00:00Z',
    updatedAt: '2026-04-01T00:00:00Z',
  } as Transaction;
}

describe('TransactionList', () => {
  it('renders a row per transaction', () => {
    render(
      <TransactionList
        transactions={[makeTx('1', 'Coffee'), makeTx('2', 'Lunch')]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onBulkDelete={vi.fn()}
      />,
    );
    expect(screen.getAllByTestId('tx-row')).toHaveLength(2);
    expect(screen.getByText('Coffee')).toBeInTheDocument();
    expect(screen.getByText('Lunch')).toBeInTheDocument();
  });

  it('shows the empty state when no transactions are passed', () => {
    render(
      <TransactionList
        transactions={[]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onBulkDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/No transactions found/i)).toBeInTheDocument();
  });

  it('renders skeleton placeholders while loading', () => {
    const { container } = render(
      <TransactionList
        transactions={[]}
        isLoading
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onBulkDelete={vi.fn()}
      />,
    );
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  // FE-PERF-003: virtualization not yet wired. Once the source imports
  // FixedSizeList from react-window, flip to a real assertion that the list
  // renders far fewer DOM rows than the underlying transactions array.
  it.skip('FE-PERF-003: virtualizes long lists via react-window (pending dep wiring)', () => {
    // Placeholder — see TransactionList.tsx around the FE-PERF-003 TODO
    // for the planned FixedSizeList implementation.
  });
});
