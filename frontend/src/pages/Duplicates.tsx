import React, { useState, useEffect } from 'react';
import api from '../services/api';
import LoadingSpinner from '../components/ui/LoadingSpinner';

interface DuplicateTx {
  id: string;
  amount: string;
  merchant: string | null;
  transaction_date: string | null;
  category: string | null;
  gmail_message_id: string | null;
}

const Duplicates: React.FC = () => {
  const [groups, setGroups] = useState<DuplicateTx[][]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchDuplicates = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<{ groups: DuplicateTx[][] }>('/transactions/duplicates');
      setGroups(res.data.groups || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load duplicates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDuplicates();
  }, []);

  const handleRemove = async (id: string) => {
    if (deleting) return;
    setDeleting(id);
    try {
      await api.delete(`/transactions/${id}`);
      await fetchDuplicates();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
        Duplicate Transactions
      </h1>
      <p className="text-gray-600 dark:text-gray-400">
        Groups of transactions that may be duplicates (same date and amount, different sources).
        Click Remove on the duplicate entry you want to delete; keep the correct one.
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner label="Loading duplicates..." />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <p className="text-red-600 dark:text-red-300">{error}</p>
        </div>
      ) : groups.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-8 text-center text-gray-500 dark:text-gray-400">
          No potential duplicates found.
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map((group, idx) => (
            <div
              key={idx}
              className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden"
            >
              <div className="px-6 py-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800">
                <span className="text-sm font-medium text-amber-800 dark:text-amber-200">
                  Group {idx + 1}: {group.length} potential duplicate(s) – same date & amount
                </span>
              </div>
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {group.map((tx) => (
                  <div
                    key={tx.id}
                    className="px-6 py-4 flex flex-wrap items-center justify-between gap-4"
                  >
                    <div className="flex flex-wrap gap-4 text-sm">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {tx.merchant || 'Unknown'}
                      </span>
                      <span className="text-gray-500 dark:text-gray-400">
                        ₹{parseFloat(tx.amount).toLocaleString('en-IN', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </span>
                      {tx.transaction_date && (
                        <span className="text-gray-500 dark:text-gray-400">
                          {new Date(tx.transaction_date).toLocaleDateString()}
                        </span>
                      )}
                      {tx.category && (
                        <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                          {tx.category}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemove(tx.id)}
                      disabled={deleting === tx.id}
                      className="px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg disabled:opacity-50"
                    >
                      {deleting === tx.id ? 'Removing...' : 'Remove'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Duplicates;
