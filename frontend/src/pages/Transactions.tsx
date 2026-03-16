import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { TransactionListResponse } from '../types';
import FilterBar from '../components/transactions/FilterBar';
import TransactionTable from '../components/transactions/TransactionTable';
import Pagination from '../components/transactions/Pagination';
import LoadingSpinner from '../components/ui/LoadingSpinner';

const Transactions: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState({
    type: searchParams.get('transaction_type') || searchParams.get('type') || '',
    merchant: searchParams.get('merchant') || '',
    startDate: searchParams.get('start_date') || '',
    endDate: searchParams.get('end_date') || '',
  });

  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, string | number> = {
        skip: (currentPage - 1) * 20,
        limit: 20,
      };

      if (filters.type) params.transaction_type = filters.type;
      if (filters.merchant) params.merchant = filters.merchant;
      if (filters.startDate) params.start_date = filters.startDate;
      if (filters.endDate) params.end_date = filters.endDate;

      const response = await api.get('/transactions', { params });
      setData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [searchParams]);

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    const params: Record<string, string> = { page: '1' };
    if (filters.type) params.transaction_type = filters.type;
    if (filters.merchant) params.merchant = filters.merchant;
    if (filters.startDate) params.start_date = filters.startDate;
    if (filters.endDate) params.end_date = filters.endDate;
    setSearchParams(params);
  };

  const resetFilters = () => {
    setFilters({
      type: '',
      merchant: '',
      startDate: '',
      endDate: '',
    });
    setSearchParams({ page: '1' });
  };

  const handlePageChange = (page: number) => {
    const params: Record<string, string> = { page: page.toString() };
    if (filters.type) params.transaction_type = filters.type;
    if (filters.merchant) params.merchant = filters.merchant;
    if (filters.startDate) params.start_date = filters.startDate;
    if (filters.endDate) params.end_date = filters.endDate;
    setSearchParams(params);
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      applyFilters();
    }, 500);
    return () => clearTimeout(timer);
  }, [filters]);

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Transactions</h1>

      <FilterBar filters={filters} onFilterChange={handleFilterChange} onReset={resetFilters} />

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner label="Loading transactions..." />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <h3 className="text-red-800 dark:text-red-400 font-medium mb-2">Error</h3>
          <p className="text-red-600 dark:text-red-300">{error}</p>
        </div>
      ) : (
        <>
          <TransactionTable transactions={data?.transactions || []} />
          {data && data.total > 0 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              hasMore={data.has_more}
              onPageChange={handlePageChange}
            />
          )}
        </>
      )}
    </div>
  );
};

export default Transactions;
