import React from 'react';
import { Insight } from '../../types';

interface InsightsPanelProps {
  insights: Insight[];
}

const typeIcons: Record<string, string> = {
  comparison: '📊',
  top_category: '🏆',
  trend: '📈',
  suggestion: '💡',
};

const InsightsPanel: React.FC<InsightsPanelProps> = ({ insights }) => {
  if (insights.length === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
        Insights
      </h2>
      <div className="space-y-3">
        {insights.map((insight, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-100 dark:border-gray-600"
          >
            <span className="text-2xl flex-shrink-0">
              {typeIcons[insight.type] || '📌'}
            </span>
            <div>
              <p className="font-medium text-gray-900 dark:text-white text-sm">
                {insight.title}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                {insight.message}
              </p>
              {insight.value && (
                <span className="inline-block mt-1 text-xs font-mono text-primary-600 dark:text-primary-400">
                  {insight.value}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default InsightsPanel;
