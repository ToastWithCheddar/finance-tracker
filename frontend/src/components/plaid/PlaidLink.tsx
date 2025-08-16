import { useState, useCallback } from 'react';
import { usePlaidLink, type PlaidLinkOnSuccess, type PlaidLinkOnExit } from 'react-plaid-link';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { usePlaidLinkToken, usePlaidActions } from '../../hooks/usePlaid';
import { Building2 } from 'lucide-react';

interface PlaidLinkProps {
  onSuccess?: () => void;
  onError?: () => void;
}

export function PlaidLink({ onSuccess, onError }: PlaidLinkProps) {
  const [isConnecting, setIsConnecting] = useState(false);

  // Get token and actions
  const { data: tokenData, isLoading: tokenLoading } = usePlaidLinkToken(true);
  const { exchangeToken } = usePlaidActions();

  // Handle Plaid success
  const handlePlaidSuccess: PlaidLinkOnSuccess = useCallback(async (publicToken, metadata) => {
    setIsConnecting(true);
    
    try {
      await exchangeToken({
        public_token: publicToken,
        metadata: {
          institution: metadata.institution,
          accounts: metadata.accounts,
        },
      });
      onSuccess?.();
    } catch (error) {
      onError?.();
    } finally {
      setIsConnecting(false);
    }
  }, [exchangeToken, onSuccess, onError]);

  // Handle Plaid exit
  const handlePlaidExit: PlaidLinkOnExit = useCallback((error) => {
    if (error) {
      onError?.();
    }
  }, [onError]);

  // Initialize Plaid
  const { open, ready } = usePlaidLink({
    token: tokenData?.link_token || '',
    onSuccess: handlePlaidSuccess,
    onExit: handlePlaidExit,
  });

  if (tokenLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <LoadingSpinner size="sm" className="mr-2" />
        <span>Loading...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Button
        onClick={open}
        disabled={!ready || isConnecting}
        className="w-full"
      >
        {isConnecting ? (
          <>
            <LoadingSpinner size="xs" className="mr-2" />
            Connecting...
          </>
        ) : (
          <>
            <Building2 className="h-4 w-4 mr-2" />
            Connect Bank Account
          </>
        )}
      </Button>
      
      <p className="text-xs text-gray-500 text-center">
        Securely connect your bank account using Plaid
      </p>
    </div>
  );
}