import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/Alert';
import { useRealtimeStore } from '../stores/realtimeStore';
import { Lightbulb, TrendingUp, AlertTriangle, DollarSign, Target, Info, AlertCircle } from 'lucide-react';
import { formatCurrency } from '../utils/currency';
import { api } from '../services/api';

interface Insight {
  id: string;
  type: string;
  title: string;
  description: string;
  priority: number;
  is_read: boolean;
  extra_payload?: Record<string, any>;
  created_at: string;
  updated_at?: string;
  transaction_id?: string;
}

interface InsightListResponse {
  insights: Insight[];
  total_count: number;
  unread_count: number;
}

// Hook for fetching insights
const useInsights = () => {
  return useQuery<InsightListResponse>({
    queryKey: ['insights'],
    queryFn: async (): Promise<InsightListResponse> => {
      const response: { data: InsightListResponse } = await api.get('/api/insights');
      return response.data;
    },
  });
};

// Insight card component
const InsightCard = ({ insight }: { insight: Insight }) => {
  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'spending_spike':
        return TrendingUp;
      case 'savings_opportunity':
        return DollarSign;
      case 'budget_alert':
        return AlertTriangle;
      case 'goal_progress':
        return Target;
      default:
        return Info;
    }
  };

  const getInsightColor = (priority: number) => {
    switch (priority) {
      case 1:
        return 'text-red-500 border-red-500/30 bg-red-500/10';
      case 2:
        return 'text-yellow-500 border-yellow-500/30 bg-yellow-500/10';
      case 3:
        return 'text-blue-500 border-blue-500/30 bg-blue-500/10';
      default:
        return 'text-[hsl(var(--text))/0.7] border-border bg-[hsl(var(--surface))]';
    }
  };

  const Icon = getInsightIcon(insight.type);
  const colorClasses = getInsightColor(insight.priority);

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)} hours ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    }
  };

  return (
    <Card className={`border-l-4 ${colorClasses} ${!insight.is_read ? 'ring-2 ring-[hsl(var(--brand))/0.35]' : ''}`}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Icon className="h-5 w-5" />
          <CardTitle className="text-lg font-semibold">{insight.title}</CardTitle>
        </div>
        {!insight.is_read && (
          <div className="h-3 w-3 bg-brand rounded-full"></div>
        )}
      </CardHeader>
      <CardContent>
        <p className="text-[hsl(var(--text))/0.85] mb-3">{insight.description}</p>
        
        {/* Action items if any */}
        {insight.extra_payload?.action_items && (
          <div className="mb-3">
            <h4 className="text-sm font-medium mb-1">Recommended Actions:</h4>
            <ul className="text-sm text-[hsl(var(--text))/0.8] list-disc list-inside">
              {insight.extra_payload.action_items.map((action: string, index: number) => (
                <li key={index}>{action}</li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Amount information if available */}
        {insight.extra_payload?.amount_cents && (
          <div className="mb-3">
            <span className="text-sm font-medium">
              Amount: {formatCurrency(insight.extra_payload.amount_cents)}
            </span>
          </div>
        )}
        
        <div className="flex items-center justify-between text-xs text-[hsl(var(--text))/0.6]">
          <span>Generated {formatTimeAgo(insight.created_at)}</span>
          <span className="capitalize">{insight.type.replace('_', ' ')}</span>
        </div>
      </CardContent>
    </Card>
  );
};

export function Insights() {
  const { data, isLoading, error, isError } = useInsights();
  const { insights: realtimeInsights } = useRealtimeStore();
  const [displayInsights, setDisplayInsights] = useState<Insight[]>([]);

  // Combine historical and real-time insights
  useEffect(() => {
    if (data?.insights) {
      // Merge historical data with real-time insights, avoiding duplicates
      const historicalInsights = data.insights;
      const allInsights = [...realtimeInsights, ...historicalInsights];
      
      // Remove duplicates by ID and sort by creation date (newest first)
      const uniqueInsights = allInsights.reduce((acc, insight) => {
        if (!acc.find(existing => existing.id === insight.id)) {
          acc.push(insight);
        }
        return acc;
      }, [] as Insight[]);
      
      uniqueInsights.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setDisplayInsights(uniqueInsights);
    }
  }, [data?.insights, realtimeInsights]);

  if (isLoading) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-6">AI Insights</h1>
        <div className="flex items-center justify-center h-32">
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-6">AI Insights</h1>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : 'Failed to load insights. Please try again.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">AI Insights</h1>
        <p className="text-[hsl(var(--text))/0.7]">
          Personalized financial insights and recommendations powered by AI
        </p>
      </div>

      {/* Summary stats */}
      {data && (
        <div className="grid gap-4 md:grid-cols-3 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Insights</CardTitle>
              <Lightbulb className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.total_count}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Unread</CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{data.unread_count}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">New Today</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {realtimeInsights.length}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Insights list */}
      <div className="space-y-4">
        {displayInsights.length === 0 ? (
          <Card>
            <CardContent className="flex items-center justify-center h-32">
              <div className="text-center">
                <Lightbulb className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">
                  No insights available yet. Check back later for personalized financial recommendations!
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          displayInsights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))
        )}
      </div>
    </div>
  );
}