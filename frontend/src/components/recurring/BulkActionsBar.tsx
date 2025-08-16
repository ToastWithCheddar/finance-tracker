import React from 'react';
import { X, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';
import { Button } from '../ui/Button';

interface BulkActionsBarProps {
  selectedCount: number;
  onActivateSelected: () => void;
  onDeactivateSelected: () => void;
  onDeleteSelected: () => void;
  onClearSelection: () => void;
  isLoading: boolean;
}

export const BulkActionsBar: React.FC<BulkActionsBarProps> = ({
  selectedCount,
  onActivateSelected,
  onDeactivateSelected,
  onDeleteSelected,
  onClearSelection,
  isLoading,
}) => {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50">
      <div className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg shadow-lg p-4">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-[hsl(var(--text))]">
            {selectedCount} rule{selectedCount > 1 ? 's' : ''} selected
          </span>
          
          <div className="flex items-center space-x-2">
            <Button
              onClick={onActivateSelected}
              disabled={isLoading}
              size="sm"
              variant="outline"
              className="text-green-600 hover:text-green-800 dark:text-green-300 dark:hover:text-green-200"
            >
              <ToggleRight className="h-4 w-4 mr-1" />
              Activate
            </Button>
            
            <Button
              onClick={onDeactivateSelected}
              disabled={isLoading}
              size="sm"
              variant="outline"
              className="text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-200"
            >
              <ToggleLeft className="h-4 w-4 mr-1" />
              Deactivate
            </Button>
            
            <Button
              onClick={onDeleteSelected}
              disabled={isLoading}
              size="sm"
              variant="outline"
              className="text-red-600 hover:text-red-800 dark:text-red-300 dark:hover:text-red-200"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete
            </Button>
          </div>
          
          <Button
            onClick={onClearSelection}
            disabled={isLoading}
            size="sm"
            variant="outline"
            className="text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-200"
          >
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        </div>
      </div>
    </div>
  );
};