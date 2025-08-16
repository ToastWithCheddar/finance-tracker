import React from 'react';
import { ResponsiveCalendar } from '@nivo/calendar';
import { useSpendingHeatmap } from '../../hooks/useDashboard';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { formatCurrency } from '../../utils';

interface SpendingHeatmapProps {
  startDate: string;
  endDate: string;
}

export const SpendingHeatmap: React.FC<SpendingHeatmapProps> = ({ startDate, endDate }) => {
  const { data, isLoading, error } = useSpendingHeatmap(startDate, endDate);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Daily Spending Heatmap</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <LoadingSpinner />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Daily Spending Heatmap</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <p>Failed to load spending heatmap</p>
            <p className="text-sm">{error instanceof Error ? error.message : 'Unknown error'}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Daily Spending Heatmap</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <p>No spending data available for the selected period</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Nivo expects values in dollars for better color scaling, not cents
  const chartData = data.map(d => ({ ...d, value: d.value / 100 }));

  // Calculate min and max values for better color scaling
  const values = chartData.map(d => d.value);
  const maxValue = Math.max(...values);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Daily Spending Heatmap</CardTitle>
        <p className="text-sm text-gray-600 mt-1">
          Visualize your daily spending patterns from {startDate} to {endDate}
        </p>
      </CardHeader>
      <CardContent className="h-[300px] pr-8">
        <ResponsiveCalendar
          data={chartData}
          from={startDate}
          to={endDate}
          emptyColor="#f3f4f6"
          colors={['#dcfce7', '#bbf7d0', '#86efac', '#4ade80', '#22c55e', '#16a34a', '#15803d']}
          margin={{ top: 40, right: 40, bottom: 40, left: 40 }}
          yearSpacing={40}
          monthBorderColor="#ffffff"
          dayBorderWidth={2}
          dayBorderColor="#ffffff"
          legends={[
            {
              anchor: 'bottom-right',
              direction: 'row',
              translateY: 36,
              itemCount: 4,
              itemWidth: 50,
              itemHeight: 36,
              itemsSpacing: 14,
              itemDirection: 'right-to-left',
              itemTextColor: '#6b7280',
              symbolSize: 20,
            },
          ]}
          tooltip={({ day, value, color }) => (
            <div className="bg-white p-3 border rounded-lg shadow-lg border-gray-200">
              <div className="flex items-center space-x-2">
                <div 
                  className="w-3 h-3 rounded" 
                  style={{ backgroundColor: color }}
                />
                <div>
                  <div className="font-medium text-gray-900">
                    {new Date(day).toLocaleDateString('en-US', { 
                      weekday: 'long', 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric' 
                    })}
                  </div>
                  <div className="text-sm text-gray-600">
                    Total spent: <span className="font-medium">{formatCurrency(value * 100)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          theme={{
            text: {
              fontSize: 12,
              fill: '#6b7280',
            },
            tooltip: {
              container: {
                background: '#ffffff',
                color: '#374151',
                fontSize: '14px',
                borderRadius: '8px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                border: '1px solid #e5e7eb',
              }
            }
          }}
        />
      </CardContent>
    </Card>
  );
};