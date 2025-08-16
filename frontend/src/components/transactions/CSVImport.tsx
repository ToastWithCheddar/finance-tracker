import { useState, useRef } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';

interface CSVImportProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (file: File) => Promise<void>;
}

interface ImportPreview {
  headers: string[];
  rows: string[][];
  validRows: number;
  invalidRows: number;
}

export function CSVImport({ isOpen, onClose, onImport }: CSVImportProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string>('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const requiredHeaders = ['amount', 'category', 'transaction_date', 'transaction_type'];
  // const optionalHeaders = ['description']; // Currently unused but kept for future functionality

  const handleFileSelect = (selectedFile: File) => {
    if (!selectedFile.name.endsWith('.csv')) {
      setError('Please select a CSV file');
      return;
    }

    setFile(selectedFile);
    setError('');
    previewFile(selectedFile);
  };

  const previewFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const csv = e.target?.result as string;
        const lines = csv.split('\n').filter(line => line.trim());
        
        if (lines.length < 2) {
          setError('CSV file must have at least a header row and one data row');
          return;
        }

        const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
        const rows = lines.slice(1).map(line => line.split(',').map(cell => cell.trim()));

        // Validate headers
        const missingHeaders = requiredHeaders.filter(header => !headers.includes(header));
        if (missingHeaders.length > 0) {
          setError(`Missing required columns: ${missingHeaders.join(', ')}`);
          return;
        }

        // Validate rows
        let validRows = 0;
        let invalidRows = 0;

        rows.forEach(row => {
          const amountIndex = headers.indexOf('amount');
          const typeIndex = headers.indexOf('transaction_type');
          const categoryIndex = headers.indexOf('category');
          const dateIndex = headers.indexOf('transaction_date');

          const amount = parseFloat(row[amountIndex]);
          const type = row[typeIndex]?.toLowerCase();
          const category = row[categoryIndex];
          const date = row[dateIndex];

          if (
            !isNaN(amount) && 
            amount > 0 && 
            ['income', 'expense'].includes(type) &&
            category &&
            date &&
            !isNaN(Date.parse(date))
          ) {
            validRows++;
          } else {
            invalidRows++;
          }
        });

        setPreview({
          headers,
          rows: rows.slice(0, 5), // Show first 5 rows for preview
          validRows,
          invalidRows
        });
      } catch {
        setError('Failed to parse CSV file');
      }
    };
    reader.readAsText(file);
  };

  const handleImport = async () => {
    if (!file) return;

    setIsProcessing(true);
    try {
      await onImport(file);
      onClose();
      setFile(null);
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const downloadTemplate = () => {
    const csvContent = [
      'amount,category,description,transaction_date,transaction_type',
      '25.50,Food & Dining,Lunch at restaurant,2024-01-15,expense',
      '3000.00,Salary,Monthly salary,2024-01-01,income',
      '45.00,Transportation,Gas,2024-01-14,expense',
      '12.99,Entertainment,Netflix subscription,2024-01-13,expense'
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'transaction_template.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Import Transactions from CSV">
      <div className="space-y-6">
        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">CSV Format Requirements</h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Required columns: <code>amount</code>, <code>category</code>, <code>transaction_date</code>, <code>transaction_type</code></li>
            <li>• Optional columns: <code>description</code></li>
            <li>• Transaction type must be either "income" or "expense"</li>
            <li>• Date format: YYYY-MM-DD (e.g., 2024-01-15)</li>
            <li>• Amount must be a positive number</li>
          </ul>
          <Button
            variant="outline"
            size="sm"
            onClick={downloadTemplate}
            className="mt-3"
          >
            📥 Download Template
          </Button>
        </div>

        {/* File Upload Area */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive 
              ? 'border-blue-400 bg-blue-50' 
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="text-4xl mb-4">📄</div>
          <p className="text-lg font-medium text-gray-900 mb-2">
            {dragActive ? 'Drop your CSV file here' : 'Upload CSV File'}
          </p>
          <p className="text-gray-500 mb-4">
            Drag and drop your file here, or click to browse
          </p>
          
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            className="hidden"
          />
          
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
          >
            Choose File
          </Button>
          
          {file && (
            <p className="text-sm text-green-600 mt-2">
              ✅ Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
            </p>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <span className="text-red-600 mr-2">⚠️</span>
              <span className="text-red-800">{error}</span>
            </div>
          </div>
        )}

        {/* Preview */}
        {preview && (
          <div className="space-y-4">
            <h4 className="font-medium text-gray-900">Import Preview</h4>
            
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <Card>
                <div className="p-3 text-center">
                  <div className="text-lg font-bold text-green-600">{preview.validRows}</div>
                  <div className="text-sm text-gray-500">Valid Rows</div>
                </div>
              </Card>
              <Card>
                <div className="p-3 text-center">
                  <div className="text-lg font-bold text-red-600">{preview.invalidRows}</div>
                  <div className="text-sm text-gray-500">Invalid Rows</div>
                </div>
              </Card>
              <Card>
                <div className="p-3 text-center">
                  <div className="text-lg font-bold text-blue-600">{preview.validRows + preview.invalidRows}</div>
                  <div className="text-sm text-gray-500">Total Rows</div>
                </div>
              </Card>
            </div>

            {/* Sample Data */}
            <div className="overflow-x-auto">
              <table className="min-w-full border border-gray-200 rounded-lg">
                <thead className="bg-gray-50">
                  <tr>
                    {preview.headers.map((header) => (
                      <th key={header} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        {header}
                        {requiredHeaders.includes(header) && (
                          <span className="text-red-500 ml-1">*</span>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {preview.rows.map((row, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex} className="px-3 py-2 text-sm text-gray-900">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {preview.invalidRows > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center">
                  <span className="text-yellow-600 mr-2">⚠️</span>
                  <span className="text-yellow-800">
                    {preview.invalidRows} row(s) will be skipped due to invalid data. Only valid rows will be imported.
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-4">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isProcessing}
          >
            Cancel
          </Button>
          
          <Button
            onClick={handleImport}
            disabled={!file || !preview || preview.validRows === 0 || isProcessing}
            className="bg-green-600 hover:bg-green-700"
          >
            {isProcessing ? 'Importing...' : `Import ${preview?.validRows || 0} Transactions`}
          </Button>
        </div>
      </div>
    </Modal>
  );
}