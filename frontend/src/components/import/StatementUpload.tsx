import React, { useState, useCallback } from 'react';
import api from '../../services/api';
import { format } from 'date-fns';

interface PreviewItem {
  amount: string;
  currency: string;
  transaction_type: string;
  merchant: string | null;
  transaction_date: string;
}

interface StatementUploadProps {
  onImportComplete?: () => void;
}

const StatementUpload: React.FC<StatementUploadProps> = ({ onImportComplete }) => {
  const [file, setFile] = useState<File | null>(null);
  const [accountLabel, setAccountLabel] = useState('');
  const [pdfPassword, setPdfPassword] = useState('');
  const [uploading, setUploading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<{ count: number; preview: PreviewItem[]; truncated: boolean } | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [drag, setDrag] = useState(false);

  const ALLOWED = ['.pdf', '.csv'];
  const MAX_CSV_MB = 5;
  const MAX_PDF_MB = 10;

  const validateFile = (f: File): string | null => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED.includes(ext)) {
      return `Invalid type. Allowed: PDF, CSV`;
    }
    const mb = f.size / 1024 / 1024;
    if (ext === '.csv' && mb > MAX_CSV_MB) return `CSV max ${MAX_CSV_MB} MB`;
    if (ext === '.pdf' && mb > MAX_PDF_MB) return `PDF max ${MAX_PDF_MB} MB`;
    return null;
  };

  const handlePreview = useCallback(async () => {
    if (!file) return;
    const err = validateFile(file);
    if (err) {
      setMessage({ type: 'error', text: err });
      return;
    }
    try {
      setPreviewing(true);
      setMessage(null);
      const form = new FormData();
      form.append('file', file);
      if (file.name.toLowerCase().endsWith('.pdf') && pdfPassword) form.append('pdf_password', pdfPassword);
      const res = await api.post('/statements/preview', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPreview(res.data);
    } catch (e: any) {
      setMessage({
        type: 'error',
        text: e.response?.data?.detail || 'Preview failed',
      });
    } finally {
      setPreviewing(false);
    }
  }, [file, pdfPassword]);

  const handleImport = useCallback(async () => {
    if (!file) return;
    const err = validateFile(file);
    if (err) {
      setMessage({ type: 'error', text: err });
      return;
    }
    try {
      setUploading(true);
      setMessage(null);
      const form = new FormData();
      form.append('file', file);
      if (accountLabel.trim()) form.append('account_label', accountLabel.trim());
      if (file.name.toLowerCase().endsWith('.pdf') && pdfPassword) form.append('pdf_password', pdfPassword);
      const res = await api.post('/statements/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage({
        type: 'success',
        text: `Imported ${res.data.created} transactions (${res.data.skipped} skipped)`,
      });
      setFile(null);
      setPreview(null);
      setPdfPassword('');
      onImportComplete?.();
    } catch (e: any) {
      setMessage({
        type: 'error',
        text: e.response?.data?.detail || 'Import failed',
      });
    } finally {
      setUploading(false);
    }
  }, [file, accountLabel, pdfPassword, onImportComplete]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      const f = e.dataTransfer.files[0];
      if (f) {
        setFile(f);
        setPreview(null);
      }
    },
    []
  );

  const onFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setPreview(null);
    }
  }, []);

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          drag
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
        }`}
      >
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Drop PDF or CSV bank/credit card statements here (max {MAX_CSV_MB} MB CSV, {MAX_PDF_MB} MB PDF)
        </p>
        <input
          type="file"
          accept=".pdf,.csv"
          onChange={onFileChange}
          className="hidden"
          id="statement-file"
        />
        <label
          htmlFor="statement-file"
          className="cursor-pointer px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg inline-block"
        >
          Choose file
        </label>
        {file && (
          <p className="mt-4 text-sm text-gray-700 dark:text-gray-300">
            Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
          </p>
        )}
      </div>

      {file && (
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Account / Card label (optional)
            </label>
            <input
              type="text"
              value={accountLabel}
              onChange={(e) => setAccountLabel(e.target.value)}
              placeholder="e.g. HDFC Credit Card, ICICI Savings"
              className="w-full max-w-md px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          {file?.name.toLowerCase().endsWith('.pdf') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                PDF password (if locked)
              </label>
              <input
                type="password"
                value={pdfPassword}
                onChange={(e) => setPdfPassword(e.target.value)}
                placeholder="Enter password if PDF is protected"
                className="w-full max-w-md px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                autoComplete="current-password"
              />
            </div>
          )}
          <div className="flex gap-3">
          <button
            onClick={handlePreview}
            disabled={previewing}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg disabled:opacity-50"
          >
            {previewing ? 'Loading...' : 'Preview'}
          </button>
          <button
            onClick={handleImport}
            disabled={uploading}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50"
          >
            {uploading ? 'Importing...' : 'Import'}
          </button>
          </div>
        </div>
      )}

      {preview && (
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <strong className="text-gray-900 dark:text-white">
              {preview.count} transaction{preview.count !== 1 ? 's' : ''} found
              {preview.truncated && ' (showing first 50)'}
            </strong>
          </div>
          <div className="max-h-64 overflow-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-100 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Date</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Type</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400">Amount</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Merchant</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {preview.preview.map((row, i) => (
                  <tr key={i} className="bg-white dark:bg-gray-900">
                    <td className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300">
                      {row.transaction_date ? format(new Date(row.transaction_date), 'dd MMM yyyy') : '-'}
                    </td>
                    <td className="px-4 py-2 text-sm capitalize">{row.transaction_type}</td>
                    <td className="px-4 py-2 text-sm text-right font-medium">
                      ₹{row.amount} {row.currency}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 truncate max-w-xs">
                      {row.merchant || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {message && (
        <p
          className={`text-sm ${
            message.type === 'error'
              ? 'text-red-600 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
          }`}
        >
          {message.text}
        </p>
      )}
    </div>
  );
};

export default StatementUpload;
