import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { SpendingByCategory } from '../../types';
import { getCurrencySymbol } from '../../utils/currency';

interface SpendingByCategoryChartProps {
  data: SpendingByCategory[];
  currency?: string;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];

const SpendingByCategoryChart: React.FC<SpendingByCategoryChartProps> = ({ data, currency = 'INR' }) => {
  const symbol = getCurrencySymbol(currency);
  const chartData = data.map((item) => ({
    name: item.category,
    value: parseFloat(item.amount),
    percentage: item.percentage,
    count: item.transaction_count,
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
        Spending by Category
      </h2>
      {chartData.length > 0 ? (
        <>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percentage }) => `${name} ${percentage.toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                }}
                formatter={(value: number, name: string, props: any) => [
                  `${symbol}${value.toLocaleString('en-IN')} (${(props.payload?.percentage || 0).toFixed(1)}%)`,
                  name,
                ]}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {data.map((item, index) => (
              <div key={item.category} className="flex items-center justify-between">
                <div className="flex items-center">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {item.category}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                    ({item.transaction_count} txns)
                  </span>
                </div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {symbol}{parseFloat(item.amount).toLocaleString('en-IN')}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="text-center text-gray-500 dark:text-gray-400 py-8">
          No category data yet. Use &quot;Auto-categorize&quot; to assign categories to transactions.
        </p>
      )}
    </div>
  );
};

export default SpendingByCategoryChart;
