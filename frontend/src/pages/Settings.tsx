import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { SyncLog } from '../types';
import { format } from 'date-fns';

const Settings: React.FC = () => {
  const { user, logout } = useAuth();
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncFromDate, setSyncFromDate] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchSyncHistory = async () => {
    try {
      const response = await api.get('/sync/history?limit=10');
      setSyncLogs(response.data);
    } catch (error) {
      console.error('Failed to fetch sync history:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSyncHistory();
  }, []);

  const runSync = async (params?: { from_date?: string; full_sync?: boolean }) => {
    try {
      setSyncing(true);
      setSyncMessage(null);
      const config = params?.full_sync
        ? { params: { full_sync: true } }
        : params?.from_date
          ? { params: { from_date: params.from_date } }
          : {};
      const res = await api.post('/sync/manual', null, config);
      setSyncMessage({
        type: 'success',
        text: res.data.message || `Processed ${res.data.emails_processed} emails, created ${res.data.transactions_created} transactions`,
      });
      fetchSyncHistory();
    } catch (e: any) {
      setSyncMessage({
        type: 'error',
        text: e.response?.data?.detail || e.response?.data?.error || 'Sync failed',
      });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>

      {/* User Information */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Account Information
        </h2>
        <div className="space-y-3">
          <div className="flex items-center">
            <div className="w-16 h-16 rounded-full bg-primary-600 flex items-center justify-center text-white text-2xl font-bold">
              {user?.name.charAt(0).toUpperCase()}
            </div>
            <div className="ml-4">
              <p className="text-lg font-medium text-gray-900 dark:text-white">{user?.name}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
            </div>
          </div>
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Account created: {user?.created_at && format(new Date(user.created_at), 'MMMM dd, yyyy')}
            </p>
          </div>
        </div>
      </div>

      {/* Email sync options */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Email Sync Options
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          If you deleted data or need to re-fetch from a specific date, use these options.
        </p>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3 items-center">
            <button
              onClick={() => runSync()}
              disabled={syncing}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50"
            >
              {syncing ? 'Syncing...' : 'Sync Now (incremental)'}
            </button>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Fetches new emails since last sync
            </span>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <input
              type="date"
              value={syncFromDate}
              onChange={(e) => setSyncFromDate(e.target.value)}
              className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
            <button
              onClick={() => syncFromDate && runSync({ from_date: syncFromDate })}
              disabled={syncing || !syncFromDate}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg disabled:opacity-50"
            >
              {syncing ? 'Syncing...' : 'Sync from this date'}
            </button>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Re-fetch emails from a specific date (e.g. after clearing data)
            </span>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <button
              onClick={() => runSync({ full_sync: true })}
              disabled={syncing}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg disabled:opacity-50"
            >
              {syncing ? 'Syncing...' : 'Full re-sync (all emails)'}
            </button>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Fetches all transaction emails from Gmail (use after deleting all data)
            </span>
          </div>
          {syncMessage && (
            <p
              className={`text-sm ${
                syncMessage.type === 'error'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-green-600 dark:text-green-400'
              }`}
            >
              {syncMessage.text}
            </p>
          )}
        </div>
      </div>

      {/* Sync History */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Sync History</h2>
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              Loading sync history...
            </div>
          ) : syncLogs.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Emails Processed
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Errors
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {syncLogs.map((log) => (
                  <tr key={log.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      {format(new Date(log.created_at), 'MMM dd, yyyy HH:mm')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          log.status === 'success'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      {log.emails_processed}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {log.errors || 'None'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No sync history available
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Actions</h2>
        <button
          onClick={logout}
          className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
        >
          Logout
        </button>
      </div>
    </div>
  );
};

export default Settings;
