import React, { useState } from 'react';
import api from '../../services/api';

const ExportButton: React.FC = () => {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    try {
      setExporting(true);
      setError(null);
      const response = await api.get('/transactions/export', {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `transactions_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Export failed. Please try again.';
      setError(message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
    <button
      onClick={handleExport}
      disabled={exporting}
      className={`px-6 py-3 rounded-lg font-medium transition-colors ${
        exporting
          ? 'bg-gray-400 cursor-not-allowed'
          : 'bg-green-600 hover:bg-green-700 text-white'
      }`}
    >
      {exporting ? (
        <span className="flex items-center">
          <svg
            className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          Exporting...
        </span>
      ) : (
        <span className="flex items-center">
          <span className="mr-2">📥</span>
          Export CSV
        </span>
      )}
    </button>
    {error && (
      <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
    )}
    </div>
  );
};

export default ExportButton;
