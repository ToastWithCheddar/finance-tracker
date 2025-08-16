import React from 'react';
import { ResponsiveSankey } from '@nivo/sankey';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useMoneyFlow } from '../../hooks/useDashboard';
import { formatCurrency } from '../../utils';
import type { MoneyFlowNode } from '../../services/dashboardService';

interface SankeyChartProps {
  startDate: string;
  endDate: string;
  className?: string;
}

export const SankeyChart: React.FC<SankeyChartProps> = ({ 
  startDate, 
  endDate,
  className = ""
}) => {
  const { data, isLoading, error } = useMoneyFlow(startDate, endDate);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Money Flow</CardTitle>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <LoadingSpinner />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Money Flow</CardTitle>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <p>Could not load money flow data</p>
            <p className="text-sm mt-1">Please try again later</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.links || data.links.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Money Flow</CardTitle>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <p>Not enough data to display money flow</p>
            <p className="text-sm mt-1">Try selecting a different date range</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Transform data for Nivo Sankey format
  const sankeyData = {
    nodes: data.nodes,
    links: data.links
  };

  // Color scheme for different node types
  const getNodeColor = (node: MoneyFlowNode) => {
    const nodeId = node.id.toLowerCase();
    if (nodeId.includes('income:')) return '#10b981'; // Green for income sources
    if (nodeId.includes('total income')) return '#3b82f6'; // Blue for total income
    if (nodeId.includes('expense:')) return '#ef4444'; // Red for expenses
    if (nodeId.includes('savings') || nodeId.includes('unaccounted')) return '#f59e0b'; // Orange for savings
    return '#6b7280'; // Gray default
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Money Flow</span>
          <div className="text-sm font-normal text-gray-500">
            {new Date(startDate).toLocaleDateString()} - {new Date(endDate).toLocaleDateString()}
          </div>
        </CardTitle>
        {data.metadata && (
          <div className="flex gap-4 text-sm text-gray-600 mt-2">
            <span>Income: {formatCurrency(data.metadata.total_income)}</span>
            <span>Expenses: {formatCurrency(data.metadata.total_expenses)}</span>
            <span>Net: {formatCurrency(data.metadata.net_savings)}</span>
          </div>
        )}
      </CardHeader>
      <CardContent className="h-[400px]">
        <ResponsiveSankey
          data={sankeyData}
          margin={{ top: 20, right: 120, bottom: 20, left: 20 }}
          align="justify"
          colors={getNodeColor}
          nodeOpacity={1}
          nodeHoverOthersOpacity={0.35}
          nodeThickness={18}
          nodeSpacing={24}
          nodeBorderWidth={0}
          nodeBorderColor={{
            from: 'color',
            modifiers: [['darker', 0.8]]
          }}
          nodeBorderRadius={3}
          linkOpacity={0.5}
          linkHoverOthersOpacity={0.1}
          linkContract={3}
          enableLinkGradient={true}
          labelPosition="outside"
          labelOrientation="vertical"
          labelPadding={16}
          labelTextColor={{
            from: 'color',
            modifiers: [['darker', 1]]
          }}
          legends={[
            {
              anchor: 'bottom-right',
              direction: 'column',
              translateX: 130,
              itemWidth: 100,
              itemHeight: 14,
              itemDirection: 'right-to-left',
              itemsSpacing: 2,
              itemTextColor: '#999',
              symbolSize: 12,
              effects: [
                {
                  on: 'hover',
                  style: {
                    itemTextColor: '#000'
                  }
                }
              ]
            }
          ]}
          nodeTooltip={({ node }) => (
            <div
              style={{
                background: 'white',
                padding: '12px 16px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              <strong>{node.id}</strong>
              <br />
              <span style={{ color: '#666' }}>
                {formatCurrency(node.value)}
              </span>
            </div>
          )}
        />
      </CardContent>
    </Card>
  );
};