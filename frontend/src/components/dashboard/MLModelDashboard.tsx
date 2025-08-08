import React, { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { Toast as ToastComponent } from '../ui/Toast';

interface MLModelPerformance {
  total_predictions: number;
  total_feedback: number;
  correct_predictions: number;
  accuracy: number;
  model_version: string;
  categories_count: number;
  users_with_feedback: number;
}

interface MLHealthStatus {
  status: string;
  model_loaded: boolean;
  prototypes_loaded: boolean;
  categories_count: number;
  model_version: string;
}

interface CategoryExample {
  category: string;
  example: string;
}

export const MLModelDashboard: React.FC = () => {
  const [performance, setPerformance] = useState<MLModelPerformance | null>(null);
  const [health, setHealth] = useState<MLHealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Add Category Example Form
  const [newExample, setNewExample] = useState<CategoryExample>({ category: '', example: '' });
  const [isAddingExample, setIsAddingExample] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  
  // Toast state
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const categories = [
    'Food & Dining',
    'Transportation',
    'Shopping',
    'Bills & Utilities',
    'Entertainment',
    'Healthcare',
    'Income'
  ];

  useEffect(() => {
    fetchMLData();
  }, []);

  const fetchMLData = async () => {
    try {
      setLoading(true);
      const [performanceRes, healthRes] = await Promise.all([
        fetch('/api/ml/performance'),
        fetch('/api/ml/health')
      ]);

      if (performanceRes.ok) {
        const perfData = await performanceRes.json();
        setPerformance(perfData);
      }

      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth(healthData);
      }
    } catch (err) {
      console.error('Error fetching ML data:', err);
      setError('Failed to load ML model data');
    } finally {
      setLoading(false);
    }
  };

  const handleAddExample = async () => {
    if (!newExample.category || !newExample.example.trim()) {
      showToast('Please fill in both category and example', 'error');
      return;
    }

    setIsAddingExample(true);
    try {
      const response = await fetch('/api/ml/add-example', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newExample),
      });

      if (!response.ok) {
        throw new Error('Failed to add example');
      }

      showToast('Example added successfully! This will improve future predictions.', 'success');
      setNewExample({ category: '', example: '' });
      fetchMLData(); // Refresh data
    } catch (error) {
      console.error('Error adding example:', error);
      showToast('Failed to add example', 'error');
    } finally {
      setIsAddingExample(false);
    }
  };

  const handleExportModel = async () => {
    setIsExporting(true);
    try {
      const response = await fetch('/api/ml/export-model', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to export model');
      }

      const result = await response.json();
      showToast(
        `Model exported successfully! ${result.quantized_path ? 'Quantized version available.' : ''}`, 
        'success'
      );
    } catch (error) {
      console.error('Error exporting model:', error);
      showToast('Failed to export model', 'error');
    } finally {
      setIsExporting(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
  };

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'unhealthy': return 'text-red-600 bg-red-100';
      default: return 'text-yellow-600 bg-yellow-100';
    }
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center">
          <LoadingSpinner />
          <span className="ml-2">Loading ML model data...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center text-red-600">
          <p>{error}</p>
          <Button onClick={fetchMLData} className="mt-4">
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">ML Model Dashboard</h2>
        <Button onClick={fetchMLData} variant="outline">
          Refresh
        </Button>
      </div>

      {/* Health Status */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Model Health Status</h3>
        {health ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center">
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getHealthStatusColor(health.status)}`}>
                {health.status.toUpperCase()}
              </div>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{health.model_loaded ? '✅' : '❌'}</p>
              <p className="text-sm text-gray-600">Model Loaded</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{health.prototypes_loaded ? '✅' : '❌'}</p>
              <p className="text-sm text-gray-600">Prototypes Loaded</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{health.categories_count}</p>
              <p className="text-sm text-gray-600">Categories</p>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">Health data unavailable</p>
        )}
      </Card>

      {/* Performance Metrics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
        {performance ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-blue-600">
                {(performance.accuracy * 100).toFixed(1)}%
              </p>
              <p className="text-sm text-gray-600">Accuracy</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-600">{performance.total_predictions}</p>
              <p className="text-sm text-gray-600">Total Predictions</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-purple-600">{performance.total_feedback}</p>
              <p className="text-sm text-gray-600">Feedback Received</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-orange-600">{performance.users_with_feedback}</p>
              <p className="text-sm text-gray-600">Active Users</p>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">Performance data unavailable</p>
        )}
      </Card>

      {/* Add Training Example */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Improve Model Training</h3>
        <p className="text-gray-600 mb-4">
          Add examples to help the model better understand transaction categories.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              value={newExample.category}
              onChange={(e) => setNewExample({ ...newExample, category: e.target.value })}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isAddingExample}
            >
              <option value="">Select category...</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Example Description
            </label>
            <input
              type="text"
              value={newExample.example}
              onChange={(e) => setNewExample({ ...newExample, example: e.target.value })}
              placeholder="e.g., coffee shop morning latte"
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isAddingExample}
            />
          </div>
          
          <div className="flex items-end">
            <Button
              onClick={handleAddExample}
              disabled={isAddingExample || !newExample.category || !newExample.example.trim()}
              className="w-full"
            >
              {isAddingExample ? 'Adding...' : 'Add Example'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Model Management */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Model Management</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <h4 className="font-medium">Model Version</h4>
              <p className="text-sm text-gray-600">
                Current: {health?.model_version || performance?.model_version || 'Unknown'}
              </p>
            </div>
            <Button
              onClick={handleExportModel}
              disabled={isExporting}
              variant="outline"
            >
              {isExporting ? 'Exporting...' : 'Export to ONNX'}
            </Button>
          </div>
          
          <div className="text-sm text-gray-500">
            <p>• ONNX export includes INT8 quantization for optimized deployment</p>
            <p>• Model uses Sentence Transformers with few-shot learning</p>
            <p>• Real-time updates from user feedback improve accuracy</p>
          </div>
        </div>
      </Card>

      {toast && (
        <ToastComponent
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
};