import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCcw } from 'lucide-react';

export const Recurring: React.FC = () => {
  const navigate = useNavigate();

  // Redirect to unified transactions page with recurring tab
  useEffect(() => {
    navigate('/transactions?tab=recurring', { replace: true });
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <RefreshCcw className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-50 animate-spin" />
        <p className="text-[hsl(var(--text))] opacity-70">
          Redirecting to unified Transactions page...
        </p>
      </div>
    </div>
  );
};