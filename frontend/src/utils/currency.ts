/**
 * Get currency symbol from currency code.
 * Supports INR, USD, EUR, GBP and falls back to code if unknown.
 */
export function getCurrencySymbol(currency: string): string {
  const symbols: Record<string, string> = {
    INR: '₹',
    USD: '$',
    EUR: '€',
    GBP: '£',
  };
  return symbols[currency?.toUpperCase()] || currency || '₹';
}

/**
 * Format amount with currency, using locale-aware number formatting.
 */
export function formatAmount(amount: string | number, currency: string = 'INR'): string {
  const symbol = getCurrencySymbol(currency);
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return `${symbol}${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
