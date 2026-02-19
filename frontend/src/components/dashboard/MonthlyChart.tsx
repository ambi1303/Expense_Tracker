import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { MonthlyData } from '../../types';

interface MonthlyChartProps {
  data: MonthlyData[];
}

const MonthlyChart: React.FC<MonthlyChartProps> = ({ data }) => {
  const chartData = data.map((item) => ({
    month: item.month,
    spent: parseFloat(item.spent),
    received: parseFloat(item.received),
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
        Monthly Trends
      </h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="month"
            stroke="#9CA3AF"
            style={{ fontSize: '12px' }}
          />
          <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#F3F4F6' }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="spent"
            stroke="#EF4444"
            strokeWidth={2}
            name="Spent"
          />
          <Line
            type="monotone"
            dataKey="received"
            stroke="#10B981"
            strokeWidth={2}
            name="Received"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MonthlyChart;
