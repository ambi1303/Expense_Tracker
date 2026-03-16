import React, { useState } from 'react';
import { Transaction, CATEGORIES } from '../../types';
import { format } from 'date-fns';
import { getCurrencySymbol } from '../../utils/currency';
import api from '../../services/api';

interface TransactionTableProps {
  transactions: Transaction[];
  onTransactionUpdated?: () => void;
}

const TransactionTable: React.FC<TransactionTableProps> = ({ transactions, onTransactionUpdated }) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleCategoryChange = async (id: string, category: string | null) => {
    if (saving) return;
    setSaving(true);
    try {
      await api.patch(`/transactions/${id}`, { category: category || null });
      onTransactionUpdated?.();
    } finally {
      setSaving(false);
      setEditingId(null);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700" role="grid">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Date
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Type
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Merchant
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Account / Card
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Category
              </th>
              <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Amount
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {transactions.length > 0 ? (
              transactions.map((transaction) => (
                <tr key={transaction.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                    {format(new Date(transaction.transaction_date), 'MMM dd, yyyy')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        transaction.transaction_type === 'debit'
                          ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                          : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                      }`}
                    >
                      {transaction.transaction_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100">
                    {transaction.merchant || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {transaction.account_label || transaction.bank_name || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {editingId === transaction.id ? (
                      <select
                        autoFocus
                        value={transaction.category || ''}
                        onChange={(e) => handleCategoryChange(transaction.id, e.target.value || null)}
                        onBlur={() => setEditingId(null)}
                        disabled={saving}
                        className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      >
                        <option value="">—</option>
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setEditingId(transaction.id)}
                        className="text-sm text-gray-700 dark:text-gray-300 hover:underline"
                      >
                        {transaction.category || 'Set category'}
                      </button>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                    <span
                      className={
                        transaction.transaction_type === 'debit'
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-green-600 dark:text-green-400'
                      }
                    >
                      {transaction.transaction_type === 'debit' ? '-' : '+'}
                      {getCurrencySymbol(transaction.currency)}
                      {parseFloat(transaction.amount).toLocaleString('en-IN', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  No transactions found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TransactionTable;
