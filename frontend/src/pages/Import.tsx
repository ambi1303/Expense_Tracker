import React from 'react';
import { useNavigate } from 'react-router-dom';
import SyncButton from '../components/dashboard/SyncButton';
import StatementUpload from '../components/import/StatementUpload';
import { useDashboardData } from '../hooks/useDashboardData';

const Import: React.FC = () => {
  const navigate = useNavigate();
  const { refetch } = useDashboardData();

  const handleImportComplete = () => {
    refetch();
    navigate('/dashboard');
  };

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Add Transactions</h1>
      <p className="text-gray-600 dark:text-gray-400">
        Choose how you want to add your transactions: sync from Gmail or upload bank/credit card statements.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Gmail Sync */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">📧</span>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Analyse via Email</h2>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Sync transaction emails from your Gmail. We analyse bank/UPI notifications and add them automatically.
          </p>
          <SyncButton onSyncComplete={handleImportComplete} />
        </div>

        {/* Statement Upload */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">📄</span>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Upload Statements</h2>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Upload bank or credit card statements (PDF or CSV). We extract and import transactions for you.
          </p>
          <StatementUpload onImportComplete={handleImportComplete} />
        </div>
      </div>
    </div>
  );
};

export default Import;
