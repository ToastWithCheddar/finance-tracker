// Remove unused React import - JSX transform is active
import { Card } from '../ui/Card';
import { useGoalStats } from '../../hooks/useGoals';
import { formatCurrency } from '../../utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export function GoalsDashboard() {
  const { data: stats, isLoading } = useGoalStats();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="p-6 animate-pulse">
            <div className="h-4 rounded w-3/4 mb-2 bg-[hsl(var(--border)/0.35)]"></div>
            <div className="h-8 rounded w-1/2 bg-[hsl(var(--border)/0.35)]"></div>
          </Card>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const progressColor = stats.average_progress >= 75 ? 'text-green-600 dark:text-green-300' : 
                       stats.average_progress >= 50 ? 'text-blue-600 dark:text-blue-300' :
                       stats.average_progress >= 25 ? 'text-yellow-600 dark:text-yellow-300' : 'text-red-600 dark:text-red-300';

  // Transform data for charts
  const typeChartData = Object.entries(stats.goals_by_type || {}).map(([type, data]: [string, { current_amount: number; count: number; total_amount: number }]) => ({
    name: type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: data.current_amount,
    count: data.count,
    target: data.total_amount,
  }));

  const trendData = stats.contribution_stats?.contribution_trend || [];

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[hsl(var(--text))] opacity-70">Total Goals</p>
              <p className="text-3xl font-bold text-[hsl(var(--text))]">{stats.total_goals}</p>
            </div>
            <div className="text-4xl">🎯</div>
          </div>
          <div className="mt-2 text-sm text-[hsl(var(--text))] opacity-70">
            {stats.active_goals} active, {stats.completed_goals} completed
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[hsl(var(--text))] opacity-70">Total Saved</p>
              <p className="text-3xl font-bold text-[hsl(var(--text))]">
                {formatCurrency(stats.total_saved_cents)}
              </p>
            </div>
            <div className="text-4xl">💰</div>
          </div>
          <div className="mt-2 text-sm text-[hsl(var(--text))] opacity-70">
            of {formatCurrency(stats.total_target_cents)} target
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[hsl(var(--text))] opacity-70">Average Progress</p>
              <p className={`text-3xl font-bold ${progressColor}`}>
                {stats.average_progress.toFixed(1)}%
              </p>
            </div>
            <div className="text-4xl">📊</div>
          </div>
          <div className="mt-2 text-sm text-[hsl(var(--text))] opacity-70">
            across all goals
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[hsl(var(--text))] opacity-70">This Month</p>
              <p className="text-3xl font-bold text-[hsl(var(--text))]">
                {formatCurrency(stats.this_month_contributions_cents)}
              </p>
            </div>
            <div className="text-4xl">📈</div>
          </div>
          <div className="mt-2 text-sm text-[hsl(var(--text))] opacity-70">
            contributions made
          </div>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Goals by Type */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Goals by Type</h3>
          {typeChartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={typeChartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent ?? 0 * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {typeChartData.map((entry: { name: string; value: number; count: number; target: number }, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number, name: string, props: any) => [
                      formatCurrency(value), 
                      `${props?.payload?.name} (${props?.payload?.count} goals)`
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-[hsl(var(--text))] opacity-60">
              No goals created yet
            </div>
          )}
        </Card>

        {/* Contribution Trend */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Monthly Contributions</h3>
          {trendData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="month" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => {
                      const [year, month] = value.split('-');
                      return `${month}/${year.slice(-2)}`;
                    }}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                  />
                  <Tooltip 
                    formatter={(value: number) => [formatCurrency(value), 'Contributions']}
                    labelFormatter={(label) => {
                      const [year, month] = label.split('-');
                      return `${new Date(parseInt(year), parseInt(month) - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}`;
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="amount" 
                    stroke="#8884d8" 
                    strokeWidth={2}
                    dot={{ fill: '#8884d8', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, stroke: '#8884d8', strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-[hsl(var(--text))] opacity-60">
              No contribution history yet
            </div>
          )}
        </Card>
      </div>

      {/* Goals Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* By Priority */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-[hsl(var(--text))]">Goals by Priority</h3>
          <div className="space-y-3">
            {Object.entries(stats.goals_by_priority || {}).map(([priority, data]: [string, { current_amount: number; total_amount: number; count: number }]) => {
              const priorityColors = {
                critical: 'bg-red-500',
                high: 'bg-orange-500',
                medium: 'bg-blue-500',
                low: 'bg-gray-500'
              };
              
              const progressPercent = data.total_amount > 0 ? 
                (data.current_amount / data.total_amount) * 100 : 0;

              return (
                <div key={priority} className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--surface))] border border-[hsl(var(--border))]">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${priorityColors[priority as keyof typeof priorityColors] || 'bg-gray-500'}`}></div>
                    <div>
                      <span className="font-medium capitalize text-[hsl(var(--text))]">{priority}</span>
                      <div className="text-sm text-[hsl(var(--text))] opacity-70">{data.count} goals</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-[hsl(var(--text))]">{formatCurrency(data.current_amount)}</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">
                      {progressPercent.toFixed(1)}% of {formatCurrency(data.total_amount)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Contribution Summary */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Contribution Summary</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
              <span className="text-green-700 font-medium">This Month</span>
              <span className="text-green-900 font-bold">
                {formatCurrency(stats.contribution_stats?.this_month_cents || 0)}
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
              <span className="text-blue-700 font-medium">Last Month</span>
              <span className="text-blue-900 font-bold">
                {formatCurrency(stats.contribution_stats?.last_month_cents || 0)}
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
              <span className="text-purple-700 font-medium">Monthly Average</span>
              <span className="text-purple-900 font-bold">
                {formatCurrency(stats.contribution_stats?.average_monthly_cents || 0)}
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
              <span className="text-gray-700 font-medium">Total Contributions</span>
              <span className="text-gray-900 font-bold">
                {formatCurrency(stats.contribution_stats?.total_contributions_cents || 0)}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {stats.average_progress < 25 && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-yellow-600">⚠️</span>
                <span className="font-medium text-yellow-800">Low Progress</span>
              </div>
              <p className="text-sm text-yellow-700">
                Your average progress is {stats.average_progress.toFixed(1)}%. 
                Consider increasing your monthly contributions.
              </p>
            </div>
          )}
          
          {stats.active_goals === 0 && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-blue-600">💡</span>
                <span className="font-medium text-blue-800">Get Started</span>
              </div>
              <p className="text-sm text-blue-700">
                You don't have any active goals. Create your first goal to start tracking your progress!
              </p>
            </div>
          )}
          
          {stats.completed_goals > 0 && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-green-600">🎉</span>
                <span className="font-medium text-green-800">Great Job!</span>
              </div>
              <p className="text-sm text-green-700">
                You've completed {stats.completed_goals} goal{stats.completed_goals > 1 ? 's' : ''}! 
                Keep up the excellent work.
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}