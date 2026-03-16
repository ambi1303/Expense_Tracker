-- Fix: Add missing columns/tables (run if GET /transactions returns 500 or budgets fail)
-- Execute: psql -U your_user -d your_db -f scripts/fix_add_account_label.sql

-- 1. Add account_label to transactions if missing
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'transactions' AND column_name = 'account_label'
  ) THEN
    ALTER TABLE transactions ADD COLUMN account_label VARCHAR(128);
    CREATE INDEX ix_transactions_account_label ON transactions(account_label);
    RAISE NOTICE 'Added account_label column and index';
  ELSE
    RAISE NOTICE 'account_label column already exists';
  END IF;
END $$;

-- 2. Create budgets table if missing
CREATE TABLE IF NOT EXISTS budgets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category VARCHAR(100) NOT NULL,
  amount NUMERIC(12,2) NOT NULL,
  period VARCHAR(20) NOT NULL DEFAULT 'monthly',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_budgets_user_id ON budgets(user_id);
CREATE INDEX IF NOT EXISTS ix_budgets_category ON budgets(category);
