export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export const CATEGORIES = [
  'Food', 'Groceries', 'Shopping', 'Transport', 'Bills',
  'Entertainment', 'Healthcare', 'Education', 'Other'
] as const;

export type Category = typeof CATEGORIES[number];

export interface Transaction {
  id: string;
  user_id: string;
  amount: string;
  currency: string;
  transaction_type: 'debit' | 'credit';
  merchant: string | null;
  transaction_date: string;
  bank_name: string | null;
  account_label: string | null;
  category: string | null;
  gmail_message_id?: string;
  created_at: string;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface Summary {
  total_spent: string;
  total_received: string;
  transaction_count: number;
  last_sync: string | null;
}

export interface MonthlyData {
  month: string;
  spent: string;
  received: string;
  transaction_count: number;
}

export interface CategoryData {
  merchant: string;
  amount: string;
  transaction_count: number;
  percentage: number;
}

export interface SyncLog {
  id: string;
  status: string;
  emails_processed: number;
  errors: string | null;
  created_at: string;
}

export interface SyncResponse {
  success: boolean;
  emails_processed: number;
  transactions_created: number;
  message: string;
  error: string | null;
}
