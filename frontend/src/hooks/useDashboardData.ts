import { useState, useEffect } from 'react';
import api from '../services/api';
import { Summary, MonthlyData, CategoryData } from '../types';

interface DashboardData {
  summary: Summary | null;
  monthlyData: MonthlyData[];
  categoryData: CategoryData[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export const useDashboardData = (): DashboardData => {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([]);
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [summaryRes, monthlyRes, categoryRes] = await Promise.all([
        api.get('/analytics/summary'),
        api.get('/analytics/monthly?months=6'),
        api.get('/analytics/categories?limit=5'),
      ]);

      setSummary(summaryRes.data);
      setMonthlyData(monthlyRes.data);
      setCategoryData(categoryRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return {
    summary,
    monthlyData,
    categoryData,
    loading,
    error,
    refetch: fetchData,
  };
};
