import { useState, useRef } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';

interface CSVImportProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (file: File) => Promise<void>;
  isLoading?: boolean;
}

interface ImportPreview {
  headers: string[];
  rows: string[][];
  validRows: number;
  invalidRows: number;
}

export function CSVImport({ isOpen, onClose, onImport, isLoading = false }: CSVImportProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [error, setError] = useState<string>('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Define expected and optional headers with better validation
  const requiredHeaders = ['amount', 'transaction_date', 'transaction_type'];
  const optionalHeaders = ['category', 'description'];
  const allValidHeaders = [...requiredHeaders, ...optionalHeaders];

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

        // Validate headers - check for required headers and warn about unknown ones
        const missingHeaders = requiredHeaders.filter(header => !headers.includes(header));
        if (missingHeaders.length > 0) {
          setError(`Missing required columns: ${missingHeaders.join(', ')}. Required: ${requiredHeaders.join(', ')}`);
          return;
        }

        // Check for unknown headers and warn (but don't error)
        const unknownHeaders = headers.filter(header => !allValidHeaders.includes(header));
        if (unknownHeaders.length > 0) {
          console.warn(`Unknown columns will be ignored: ${unknownHeaders.join(', ')}`);
        }

        // Validate rows
        let validRows = 0;
        let invalidRows = 0;

        rows.forEach((row, rowIndex) => {
          const amountIndex = headers.indexOf('amount');
          const typeIndex = headers.indexOf('transaction_type');
          const categoryIndex = headers.indexOf('category');
          const dateIndex = headers.indexOf('transaction_date');
          const descriptionIndex = headers.indexOf('description');

          // More robust validation
          const amount = parseFloat(row[amountIndex]);
          const type = row[typeIndex]?.toLowerCase().trim();
          const category = row[categoryIndex]?.trim();
          const date = row[dateIndex]?.trim();
          const description = row[descriptionIndex]?.trim();

          // Validation with detailed error tracking
          let isValid = true;
          const rowErrors: string[] = [];

          // Amount validation
          if (isNaN(amount) || amount <= 0) {
            isValid = false;
            rowErrors.push('invalid amount');
          }

          // Type validation - more flexible
          if (!type || !['income', 'expense', 'credit', 'debit'].includes(type)) {
            isValid = false;
            rowErrors.push(`invalid transaction_type: '${type}' (expected: income/expense)`);
          }

          // Date validation - support multiple formats
          let parsedDate = null;
          if (!date) {
            isValid = false;
            rowErrors.push('missing date');
          } else {
            // Try multiple date formats
            const dateFormats = [
              /^\d{4}-\d{2}-\d{2}$/, // YYYY-MM-DD
              /^\d{2}\/\d{2}\/\d{4}$/, // MM/DD/YYYY
              /^\d{2}-\d{2}-\d{4}$/, // MM-DD-YYYY
            ];
            
            const isValidDateFormat = dateFormats.some(format => format.test(date));
            parsedDate = new Date(date);
            
            if (!isValidDateFormat || isNaN(parsedDate.getTime())) {
              isValid = false;
              rowErrors.push(`invalid date format: '${date}' (expected: YYYY-MM-DD, MM/DD/YYYY, or MM-DD-YYYY)`);
            }
          }

          // Category is now optional but warn if missing
          if (!category && categoryIndex !== -1) {
            console.warn(`Row ${rowIndex + 2}: Missing category, will be auto-categorized`);
          }

          if (isValid) {
            validRows++;
          } else {
            invalidRows++;
            console.warn(`Row ${rowIndex + 2} invalid:`, rowErrors.join(', '));
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
    setImportProgress(0);
    setError('');
    
    try {
      // Simulate progress updates during import
      const progressInterval = setInterval(() => {
        setImportProgress(prev => {
          if (prev >= 90) return prev;
          return prev + Math.random() * 20;
        });
      }, 200);

      await onImport(file);
      
      // Clear progress interval and set to 100%
      clearInterval(progressInterval);
      setImportProgress(100);
      
      // Small delay to show completion
      await new Promise(resolve => setTimeout(resolve, 500));
      
      onClose();
      setFile(null);
      setPreview(null);
      setImportProgress(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
      setImportProgress(0);
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
      'amount,transaction_date,transaction_type,category,description',
      '25.50,2024-01-15,expense,Food & Dining,Lunch at restaurant',
      '3000.00,2024-01-01,income,Salary,Monthly salary',
      '45.00,2024-01-14,expense,Transportation,Gas',
      '12.99,2024-01-13,expense,Entertainment,Netflix charge',
      '50.00,01/20/2024,expense,,Groceries without category'
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
            <li>• <strong>Required columns:</strong> <code>amount</code>, <code>transaction_date</code>, <code>transaction_type</code></li>
            <li>• <strong>Optional columns:</strong> <code>category</code>, <code>description</code></li>
            <li>• <strong>Transaction type:</strong> "income", "expense", "credit", or "debit"</li>
            <li>• <strong>Date formats:</strong> YYYY-MM-DD, MM/DD/YYYY, or MM-DD-YYYY</li>
            <li>• <strong>Amount:</strong> Must be a positive number (expenses will be automatically converted)</li>
            <li>• <strong>Category:</strong> If missing, transactions will be auto-categorized using AI</li>
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

        {/* Progress Indicator */}
        {isProcessing && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Importing transactions...
              </span>
              <span className="text-sm text-gray-500">
                {Math.round(importProgress)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${importProgress}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 text-center">
              {importProgress < 30 && "Processing CSV file..."}
              {importProgress >= 30 && importProgress < 70 && "Validating transaction data..."}
              {importProgress >= 70 && importProgress < 95 && "Saving transactions to database..."}
              {importProgress >= 95 && "Finalizing import..."}
            </div>
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
            className="bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Importing...
              </div>
            ) : (
              `Import ${preview?.validRows || 0} Transactions`
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
