import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { CATEGORIES } from '../types';
import LoadingSpinner from '../components/ui/LoadingSpinner';

interface Budget {
  id: string;
  user_id: string;
  category: string;
  amount: string;
  period: string;
  created_at: string;
}

interface BudgetSummaryItem {
  category: string;
  budget_amount: string;
  spent: string;
  remaining: string;
  percent_used: number;
  over_budget: boolean;
}

interface BudgetSummary {
  items: BudgetSummaryItem[];
  total_budget: string;
  total_spent: string;
}

const Budgets: React.FC = () => {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newCategory, setNewCategory] = useState('');
  const [newAmount, setNewAmount] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [budgetsRes, summaryRes] = await Promise.all([
        api.get<Budget[]>('/budgets'),
        api.get<BudgetSummary>('/budgets/summary'),
      ]);
      setBudgets(budgetsRes.data);
      setSummary(summaryRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load budgets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCategory || !newAmount || parseFloat(newAmount) <= 0) return;
    setSaving(true);
    try {
      await api.post('/budgets', {
        category: newCategory,
        amount: parseFloat(newAmount),
        period: 'monthly',
      });
      setNewCategory('');
      setNewAmount('');
      setShowAdd(false);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add budget');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/budgets/${id}`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const formatAmount = (n: string | number) =>
    parseFloat(String(n)).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Budgets</h1>
      <p className="text-gray-600 dark:text-gray-400">
        Set monthly budget limits per category and track spending.
      </p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner label="Loading budgets..." />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <p className="text-red-600 dark:text-red-300">{error}</p>
        </div>
      ) : (
        <>
          {/* Summary cards */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Budget</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  ₹{formatAmount(summary.total_budget)}
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Spent (This Month)</p>
                <p className="text-xl font-bold text-red-600 dark:text-red-400">
                  ₹{formatAmount(summary.total_spent)}
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4">
                <p className="text-sm text-gray-500 dark:text-gray-400">Remaining</p>
                <p className="text-xl font-bold text-green-600 dark:text-green-400">
                  ₹{formatAmount(
                    parseFloat(summary.total_budget) - parseFloat(summary.total_spent)
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Add budget form */}
          {showAdd ? (
            <form
              onSubmit={handleAddBudget}
              className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-6"
            >
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Add Budget
              </h3>
              <div className="flex flex-wrap gap-4 items-end">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Category
                  </label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    required
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="">Select...</option>
                    {CATEGORIES.filter((c) => !budgets.some((b) => b.category === c)).map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Amount (₹/month)
                  </label>
                  <input
                    type="number"
                    min="1"
                    step="0.01"
                    value={newAmount}
                    onChange={(e) => setNewAmount(e.target.value)}
                    required
                    placeholder="e.g. 5000"
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white w-32"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                  >
                    {saving ? 'Adding...' : 'Add'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowAdd(false); setNewCategory(''); setNewAmount(''); }}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          ) : (
            <button
              onClick={() => setShowAdd(true)}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              + Add Budget
            </button>
          )}

          {/* Summary by category */}
          {summary && summary.items.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Spend vs Budget (This Month)
                </h2>
              </div>
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {summary.items.map((item) => (
                  <div
                    key={item.category}
                    className="px-6 py-4 flex flex-wrap items-center justify-between gap-4"
                  >
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {item.category}
                      </span>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        ₹{formatAmount(item.spent)} / ₹{formatAmount(item.budget_amount)} (
                        {item.percent_used.toFixed(0)}% used)
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span
                        className={
                          item.over_budget
                            ? 'text-red-600 dark:text-red-400 font-medium'
                            : 'text-green-600 dark:text-green-400'
                        }
                      >
                        {item.over_budget ? 'Over' : 'Under'} budget
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* List budgets */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Your Budgets</h2>
            </div>
            {budgets.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                No budgets set. Add one above.
              </div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {budgets.map((b) => (
                  <div
                    key={b.id}
                    className="px-6 py-4 flex items-center justify-between"
                  >
                    <span className="font-medium text-gray-900 dark:text-white">
                      {b.category}
                    </span>
                    <div className="flex items-center gap-4">
                      <span className="text-gray-600 dark:text-gray-400">
                        ₹{formatAmount(b.amount)}/month
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDelete(b.id)}
                        className="text-sm text-red-600 dark:text-red-400 hover:underline"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default Budgets;
