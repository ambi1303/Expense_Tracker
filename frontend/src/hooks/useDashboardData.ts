import { useState, useEffect } from 'react';
import api from '../services/api';
import { Summary, MonthlyData, CategoryData, SpendingByCategory, Insight } from '../types';

interface DashboardData {
  summary: Summary | null;
  monthlyData: MonthlyData[];
  categoryData: CategoryData[];
  spendingByCategory: SpendingByCategory[];
  insights: Insight[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  autoCategorize: () => Promise<number>;
}

export const useDashboardData = (): DashboardData => {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([]);
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [spendingByCategory, setSpendingByCategory] = useState<SpendingByCategory[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [summaryRes, monthlyRes, categoryRes, byCategoryRes, insightsRes] = await Promise.all([
        api.get('/analytics/summary'),
        api.get('/analytics/monthly?months=6'),
        api.get('/analytics/categories?limit=5'),
        api.get('/analytics/by-category?limit=8&months=6'),
        api.get('/analytics/insights'),
      ]);

      setSummary(summaryRes.data);
      setMonthlyData(monthlyRes.data);
      setCategoryData(categoryRes.data);
      setSpendingByCategory(byCategoryRes.data || []);
      setInsights(insightsRes.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const autoCategorize = async (): Promise<number> => {
    const res = await api.post('/transactions/auto-categorize');
    const updated = (res.data as { updated: number }).updated;
    if (updated > 0) {
      await fetchData();
    }
    return updated;
  };

  useEffect(() => {
    fetchData();
  }, []);

  return {
    summary,
    monthlyData,
    categoryData,
    spendingByCategory,
    insights,
    loading,
    error,
    refetch: fetchData,
    autoCategorize,
  };
};
