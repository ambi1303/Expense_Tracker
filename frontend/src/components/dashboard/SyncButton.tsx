import React, { useState } from 'react';
import api from '../../services/api';

interface SyncButtonProps {
  onSyncComplete: () => void;
}

const SyncButton: React.FC<SyncButtonProps> = ({ onSyncComplete }) => {
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSync = async () => {
    try {
      setSyncing(true);
      setMessage(null);
      const response = await api.post('/sync/manual');
      setMessage(response.data.message || 'Sync completed successfully');
      onSyncComplete();
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Sync failed');
    } finally {
      setSyncing(false);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  return (
    <div>
      <button
        onClick={handleSync}
        disabled={syncing}
        className={`px-6 py-3 rounded-lg font-medium transition-colors ${
          syncing
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-primary-600 hover:bg-primary-700 text-white'
        }`}
      >
        {syncing ? (
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
            Syncing...
          </span>
        ) : (
          <span className="flex items-center">
            <span className="mr-2">🔄</span>
            Sync Now
          </span>
        )}
      </button>
      {message && (
        <p
          className={`mt-2 text-sm ${
            message.includes('failed') || message.includes('error')
              ? 'text-red-600 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
          }`}
        >
          {message}
        </p>
      )}
    </div>
  );
};

export default SyncButton;
