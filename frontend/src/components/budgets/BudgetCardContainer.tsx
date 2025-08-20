import { useState } from 'react';
import { BudgetCard } from './BudgetCard';
import { BudgetAlertSettings } from './BudgetAlertSettings';
import { BudgetCalendar } from './BudgetCalendar';
import type { Budget } from '../../types/budgets';

interface BudgetCardContainerProps {
  budget: Budget;
  onEdit: (budget: Budget) => void;
  onDelete: (budgetId: string) => void;
  isLoading?: boolean;
}

export function BudgetCardContainer({ 
  budget, 
  onEdit, 
  onDelete, 
  isLoading = false 
}: BudgetCardContainerProps) {
  const [showAlertSettings, setShowAlertSettings] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);

  return (
    <>
      <BudgetCard
        budget={budget}
        onEdit={onEdit}
        onDelete={onDelete}
        isLoading={isLoading}
        onOpenAlertSettings={() => setShowAlertSettings(true)}
        onOpenCalendar={() => setShowCalendar(true)}
      />

      {/* Modal components managed by container */}
      <BudgetAlertSettings
        budget={budget}
        isOpen={showAlertSettings}
        onClose={() => setShowAlertSettings(false)}
      />

      <BudgetCalendar
        budget={budget}
        isOpen={showCalendar}
        onClose={() => setShowCalendar(false)}
      />
    </>
  );
}