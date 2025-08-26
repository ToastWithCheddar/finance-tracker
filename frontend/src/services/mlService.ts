import { api } from './api';

export interface MLCategorizeRequest {
  description: string;
  amount: number;
}

export interface MLCategorizeResponse {
  category_id: string;
  confidence: number;
  confidence_level: string;
  model_version: string;
  all_similarities?: Record<string, number>;
}


export interface MLPerformanceMetrics {
  total_predictions: number;
  total_feedback: number;
  correct_predictions: number;
  accuracy: number;
  model_version: string;
  categories_count: number;
  users_with_feedback: number;
}

export interface MLHealthStatus {
  status: string;
  model_loaded: boolean;
  prototypes_loaded: boolean;
  categories_count: number;
  model_version: string;
}

export interface BatchCategorizeRequest {
  transactions: Array<{
    id: string;
    description: string;
    amount: number;
  }>;
}

export interface BatchCategorizeResponse {
  results: Array<{
    id: string;
    prediction?: {
      categoryId: string;
      confidence: number;
    };
  }>;
}

export interface CategoryExampleRequest {
  category: string;
  example: string;
}

class MLService {
  /**
   * Categorize a single transaction using ML model
   */
  async categorizeTransaction(request: MLCategorizeRequest): Promise<MLCategorizeResponse> {
    return await api.post<MLCategorizeResponse>('/ml/categorize', request);
  }

  /**
   * Categorize multiple transactions in batch
   */
  async batchCategorizeTransactions(request: BatchCategorizeRequest): Promise<BatchCategorizeResponse> {
    return await api.post<BatchCategorizeResponse>('/ml/batch-categorize', request);
  }


  /**
   * Add a new example to a category for training
   */
  async addCategoryExample(request: CategoryExampleRequest) {
    return await api.post('/ml/add-example', request);
  }

  /**
   * Export model to ONNX format with quantization
   */
  async exportModel() {
    return await api.post('/ml/export-model');
  }

  /**
   * Get model performance metrics
   */
  async getModelPerformance(): Promise<MLPerformanceMetrics> {
    return await api.get<MLPerformanceMetrics>('/ml/performance');
  }

  /**
   * Get ML system health status
   */
  async getHealthStatus(): Promise<MLHealthStatus> {
    return await api.get<MLHealthStatus>('/ml/health');
  }

  /**
   * Auto-categorize a transaction with confidence threshold
   * Only returns a category if confidence is above threshold
   */
  async autoCategorizeSafe(
    request: MLCategorizeRequest, 
    confidenceThreshold: number = 0.8
  ): Promise<MLCategorizeResponse | null> {
    try {
      const result = await this.categorizeTransaction(request);
      
      if (result.confidence >= confidenceThreshold) {
        return result;
      }
      
      return null; // Low confidence, let user decide
    } catch (error: unknown) {
      console.error('Auto-categorization failed:', error);
      return null;
    }
  }

  /**
   * Get category suggestions with all confidence levels
   * Useful for showing multiple options to user
   */
  async getCategorySuggestions(request: MLCategorizeRequest) {
    try {
      const result = await this.categorizeTransaction(request);
      
      // Sort similarities by confidence
      const suggestions = Object.entries(result.all_similarities || {})
        .map(([category, confidence]) => ({ category, confidence }))
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, 3); // Top 3 suggestions
      
      return {
        primary: {
          category: result.category_id,
          confidence: result.confidence,
          level: result.confidence_level
        },
        suggestions,
        model_version: result.model_version
      };
    } catch (error: unknown) {
      console.error('Failed to get category suggestions:', error);
      return null;
    }
  }

  /**
   * Bulk upload training examples from CSV or similar
   */
  async bulkAddExamples(examples: CategoryExampleRequest[]) {
    const results = [];
    
    for (const example of examples) {
      try {
        const result = await this.addCategoryExample(example);
        results.push({ ...example, status: 'success', result });
      } catch (error: any) {
        results.push({ ...example, status: 'error', error: error?.message ?? String(error) });
      }
    }
    
    return results;
  }

  /**
   * Check if ML service is available
   */
  async isMLServiceAvailable(): Promise<boolean> {
    try {
      const health = await this.getHealthStatus();
      return health.status === 'healthy' && health.model_loaded;
    } catch {
      return false;
    }
  }

  /**
   * Get model training suggestions based on user's transaction history
   */
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async getTrainingSuggestions(_userId: string) {
    // This would analyze user's correction patterns and suggest
    // categories that need more training examples
    try {
      const performance = await this.getModelPerformance();
      
      // Mock implementation - in reality, this would analyze
      // which categories have low accuracy for this user
      return {
        suggested_categories: [
          { category: 'Food & Dining', reason: 'Low accuracy on restaurant transactions' },
          { category: 'Transportation', reason: 'Rideshare transactions often misclassified' }
        ],
        overall_accuracy: performance.accuracy,
        user_feedback_count: performance.total_feedback
      };
    } catch (error: unknown) {
      console.error('Failed to get training suggestions:', error);
      return null;
    }
  }

  /**
   * Real-time classification for transaction entry
   * Provides immediate feedback as user types
   */
  async getLiveClassification(
    description: string,
    amount?: number,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _debounceMs: number = 500
  ): Promise<MLCategorizeResponse | null> {
    if (!description || description.length < 3) {
      return null;
    }

    // Debounce mechanism would be handled by the calling component
    try {
      return await this.categorizeTransaction({
        description,
        amount: amount || 0
      });
    } catch (error: unknown) {
      console.error('Live classification failed:', error);
      return null;
    }
  }
}

export const mlService = new MLService();
