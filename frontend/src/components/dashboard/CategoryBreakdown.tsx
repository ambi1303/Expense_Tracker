import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { CategoryData } from '../../types';

interface CategoryBreakdownProps {
  data: CategoryData[];
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({ data }) => {
  const chartData = data.map((item) => ({
    name: item.merchant,
    value: parseFloat(item.amount),
    percentage: item.percentage,
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
        Top Spending Categories
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
                label={({ percentage }) => `${percentage.toFixed(1)}%`}
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
                formatter={(value: number) => `₹${value.toLocaleString('en-IN')}`}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {data.map((item, index) => (
              <div key={item.merchant} className="flex items-center justify-between">
                <div className="flex items-center">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  ></div>
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {item.merchant}
                  </span>
                </div>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  ₹{parseFloat(item.amount).toLocaleString('en-IN')}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="text-center text-gray-500 dark:text-gray-400 py-8">
          No spending data available
        </p>
      )}
    </div>
  );
};

export default CategoryBreakdown;
