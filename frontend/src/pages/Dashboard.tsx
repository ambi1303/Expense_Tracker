import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useDashboardData } from '../hooks/useDashboardData';
import SummaryCards from '../components/dashboard/SummaryCards';
import MonthlyChart from '../components/dashboard/MonthlyChart';
import CategoryBreakdown from '../components/dashboard/CategoryBreakdown';
import SpendingByCategoryChart from '../components/dashboard/SpendingByCategoryChart';
import InsightsPanel from '../components/dashboard/InsightsPanel';
import SyncButton from '../components/dashboard/SyncButton';
import ExportButton from '../components/dashboard/ExportButton';
import LoadingSpinner from '../components/ui/LoadingSpinner';

const Dashboard: React.FC = () => {
  const { summary, monthlyData, categoryData, spendingByCategory, insights, loading, error, refetch, autoCategorize } = useDashboardData();
  const [categorizing, setCategorizing] = useState(false);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner label="Loading dashboard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <h3 className="text-red-800 dark:text-red-400 font-medium mb-2">Error</h3>
        <p className="text-red-600 dark:text-red-300">{error}</p>
        <button
          onClick={refetch}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={async () => {
              setCategorizing(true);
              try {
                const n = await autoCategorize();
                if (n > 0) alert(`Categorized ${n} transactions`);
              } finally {
                setCategorizing(false);
              }
            }}
            disabled={categorizing}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg disabled:opacity-50"
          >
            {categorizing ? 'Categorizing...' : 'Auto-categorize'}
          </button>
          <SyncButton onSyncComplete={refetch} />
          <ExportButton />
        </div>
      </div>

      {summary && <SummaryCards summary={summary} />}

      {insights.length > 0 && <InsightsPanel insights={insights} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {monthlyData.length > 0 && <MonthlyChart data={monthlyData} />}
        {spendingByCategory.length > 0 ? (
          <SpendingByCategoryChart data={spendingByCategory} />
        ) : (
          categoryData.length > 0 && <CategoryBreakdown data={categoryData} />
        )}
      </div>

      {summary?.transaction_count === 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6 text-center">
          <p className="text-blue-800 dark:text-blue-400 font-medium mb-2">
            No transactions yet
          </p>
          <p className="text-blue-600 dark:text-blue-300 mb-4">
            Go to <Link to="/import" className="underline font-medium">Add Data</Link> to sync from Gmail or upload statements (PDF/CSV)
          </p>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
