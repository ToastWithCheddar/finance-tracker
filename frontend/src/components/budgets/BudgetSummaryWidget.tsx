import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { budgetService } from '../../services/budgetService';
import { useBudgetSummary } from '../../hooks/useBudgets';
import { DollarSign, Wallet, PiggyBank } from 'lucide-react';

interface BudgetSummaryWidgetProps {
  className?: string;
  showTitle?: boolean;
}

export function BudgetSummaryWidget({ className = '', showTitle = true }: BudgetSummaryWidgetProps) {
  const { data: summary, isLoading, error } = useBudgetSummary();

  return (
    <Card className={className}>
      {showTitle && (
        <CardHeader>
          <CardTitle>Budget Summary</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        {isLoading ? (
          <div className="h-20 animate-pulse bg-[hsl(var(--border)/0.35)] rounded" />
        ) : error ? (
          <p className="text-sm text-red-600">Failed to load budget summary.</p>
        ) : summary ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--border)/0.35)]">
              <div>
                <p className="text-xs text-[hsl(var(--text))/0.7]">Total Budgeted</p>
                <p className="text-lg font-semibold text-green-600">{budgetService.formatCurrency(summary.total_budgeted_cents)}</p>
              </div>
              <DollarSign className="h-5 w-5 text-green-600" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--border)/0.35)]">
              <div>
                <p className="text-xs text-[hsl(var(--text))/0.7]">Total Spent</p>
                <p className="text-lg font-semibold text-red-600">{budgetService.formatCurrency(summary.total_spent_cents)}</p>
              </div>
              <Wallet className="h-5 w-5 text-red-600" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--border)/0.35)]">
              <div>
                <p className="text-xs text-[hsl(var(--text))/0.7]">Remaining</p>
                <p className="text-lg font-semibold text-blue-600">{budgetService.formatCurrency(summary.total_remaining_cents)}</p>
              </div>
              <PiggyBank className="h-5 w-5 text-blue-600" />
            </div>
          </div>
        ) : (
          <p className="text-sm text-[hsl(var(--text))/0.7]">No budget data available.</p>
        )}
      </CardContent>
    </Card>
  );
}

export default BudgetSummaryWidget;

