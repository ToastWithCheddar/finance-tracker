import { useState, useCallback, useEffect } from 'react';
import { usePlaidLink, type PlaidLinkOnSuccess, type PlaidLinkOnExit} from 'react-plaid-link';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui';
import { usePlaidLinkToken, usePlaidActions } from '../../hooks/usePlaid';
import { Building2, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

type PlaidError = { error_message?: string } & Record<string, unknown>;

interface PlaidLinkProps {
  onSuccess?: (accounts: unknown[]) => void;
  onError?: (error: unknown) => void;
  className?: string;
}

export function PlaidLink({ onSuccess, onError, className }: PlaidLinkProps) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionResult, setConnectionResult] = useState<{
    success: boolean;
    message: string;
    accounts?: unknown[];
  } | null>(null);

  // Get link token when component mounts
  const { data: linkTokenData, isLoading: isLoadingToken, error: tokenError } = usePlaidLinkToken(true);
  
  const { exchangeToken, isExchanging, exchangeError, exchangeResult, syncTransactions, syncBalances } = usePlaidActions();

  // Handle successful Plaid Link
  const onPlaidSuccess: PlaidLinkOnSuccess = useCallback(
    async (publicToken, metadata) => {
      try {
        setIsConnecting(true);
        
        console.log('🔗 Plaid Link Success:', { publicToken, metadata });
        
        // Exchange the public token for an access token
        // Handle case where institution metadata might be null
        if (!metadata.institution) {
          throw new Error('Institution information is required for bank connection');
        }

        exchangeToken({
          public_token: publicToken,
          metadata: {
            institution: metadata.institution,
            accounts: metadata.accounts,
          },
        });
        
      } catch (error) {
        console.error('❌ Failed to exchange token:', error);
        const errorMessage = error instanceof Error ? error.message : 'Failed to connect bank account';
        setConnectionResult({
          success: false,
          message: errorMessage,
        });
        onError?.(error);
      } finally {
        setIsConnecting(false);
      }
    },
    [exchangeToken, onError]
  );

  // Handle exchange token success
  useEffect(() => {
    if (exchangeResult) {
      console.log('✅ Token exchange successful:', exchangeResult);
      setConnectionResult({
        success: true,
        message: exchangeResult.message || 'Bank account connected successfully!',
        accounts: exchangeResult.accounts,
      });
      onSuccess?.(exchangeResult.accounts);

      // Trigger background syncs to populate data immediately
      try {
        syncTransactions(undefined);
        syncBalances(undefined);
      } catch (e) {
        // Non-blocking
        console.warn('Sync trigger failed:', e);
      }
    }
  }, [exchangeResult, onSuccess]);

  // Handle exchange error
  useEffect(() => {
    if (exchangeError) {
      console.error('❌ Token exchange failed:', exchangeError);
      const errorMessage = 'Failed to connect bank account. Please try again.';
      setConnectionResult({
        success: false,
        message: errorMessage,
      });
      onError?.(exchangeError);
    }
  }, [exchangeError, onError]);

  // Handle Plaid Link error
  const onPlaidError = useCallback(
    (error: PlaidError) => {
      console.error('❌ Plaid Link Error:', error);
      setConnectionResult({
        success: false,
        message: (error.error_message as string) || 'Failed to connect to your bank. Please try again.',
      });
      onError?.(error);
    },
    [onError]
  );

  // Handle Plaid Link exit
  const onPlaidExit: PlaidLinkOnExit = useCallback(
    (error, metadata) => {
      if (error) {
        console.error('❌ Plaid Link Exit Error:', error, metadata);
        onError?.(error);
      } else {
        console.log('👋 User exited Plaid Link', metadata);
      }
    }, [onError]);

  // Initialize Plaid Link - always call the hook but conditionally use it
  const plaidLinkConfig = {
    token: linkTokenData?.link_token || '',
    onSuccess: onPlaidSuccess,
    onExit: onPlaidExit,
  };
  
  const { open: openPlaidLink, ready: plaidLinkReady } = usePlaidLink(plaidLinkConfig);
  
  // Only enable if we have a valid token
  const isPlaidReady = linkTokenData?.link_token && plaidLinkReady;

  // Handle connect button click
  const handleConnect = useCallback(() => {
    setConnectionResult(null);
    openPlaidLink();
  }, [openPlaidLink]);

  // Clear result after some time
  useEffect(() => {
    if (connectionResult) {
      const timer = setTimeout(() => {
        setConnectionResult(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [connectionResult]);

  // Loading state while getting token
  if (isLoadingToken) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <LoadingSpinner size="sm" className="mr-2" />
        <span className="text-sm text-gray-600">Initializing bank connection...</span>
      </div>
    );
  }

  // Error state
  if (tokenError) {
    return (
      <div className={`flex items-center p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}>
        <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
        <span className="text-sm text-red-700">
          Failed to initialize bank connection. Please try again later.
        </span>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Connection Result */}
      {connectionResult && (
        <div
          className={`mb-4 p-4 rounded-lg border ${
            connectionResult.success
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          <div className="flex items-center">
            {connectionResult.success ? (
              <CheckCircle className="h-5 w-5 mr-2" />
            ) : (
              <AlertCircle className="h-5 w-5 mr-2" />
            )}
            <span className="text-sm font-medium">{connectionResult.message}</span>
          </div>
          {connectionResult.accounts && connectionResult.accounts.length > 0 && (
            <div className="mt-2 text-xs">
              Connected {connectionResult.accounts.length} account(s)
            </div>
          )}
        </div>
      )}

      {/* Connect Button */}
      <Button
        onClick={handleConnect}
        disabled={!isPlaidReady || isConnecting || isExchanging}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white"
      >
        {isConnecting || isExchanging ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            {isConnecting ? 'Connecting...' : 'Setting up account...'}
          </>
        ) : (
          <>
            <Building2 className="h-4 w-4 mr-2" />
            Connect Bank Account
          </>
        )}
      </Button>

      {/* Help text */}
      <p className="mt-2 text-xs text-gray-500 text-center">
        Securely connect your bank account using Plaid. Your credentials are never stored.
      </p>
    </div>
  );
}