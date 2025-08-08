// ML service integration types

export interface MLCategoryPrediction {
  categoryId: string;
  categoryName: string;
  confidence: number;
  reasoning: string;
  alternativeCategories?: Array<{
    categoryId: string;
    categoryName: string;
    confidence: number;
  }>;
}

export interface MLConfidenceScore {
  score: number; // 0-1 range
  level: 'low' | 'medium' | 'high';
  threshold: {
    autoApply: number; // Confidence needed to auto-apply
    suggest: number;   // Confidence needed to suggest
    minimum: number;   // Minimum confidence to show
  };
}

export interface MLFeedback {
  transactionId: string;
  predictedCategoryId: string;
  actualCategoryId: string;
  userConfirmed: boolean;
  feedbackType: 'correction' | 'confirmation' | 'rejection';
  timestamp: string;
  confidence: number;
  reasoning?: string;
}

export interface MLTrainingData {
  transactionDescription: string;
  merchant?: string;
  amount: number;
  categoryId: string;
  userId: string;
  feedback: MLFeedback[];
}

export interface MLModelPerformance {
  modelVersion: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  lastUpdated: string;
  totalPredictions: number;
  correctPredictions: number;
  userCorrections: number;
}

export interface MLCategorizeRequest {
  description: string;
  merchant?: string;
  amountCents: number;
  accountId?: string;
  userId?: string;
  includeAlternatives?: boolean;
  minConfidence?: number;
}

export interface MLCategorizeResponse {
  prediction: MLCategoryPrediction;
  confidence: MLConfidenceScore;
  modelVersion: string;
  processingTime: number;
  shouldAutoApply: boolean;
  shouldSuggest: boolean;
}

export interface MLBatchCategorizeRequest {
  transactions: Array<{
    id?: string;
    description: string;
    merchant?: string;
    amountCents: number;
  }>;
  userId?: string;
  includeAlternatives?: boolean;
  minConfidence?: number;
}

export interface MLBatchCategorizeResponse {
  results: Array<{
    transactionId?: string;
    index: number;
    prediction: MLCategoryPrediction;
    confidence: MLConfidenceScore;
    shouldAutoApply: boolean;
    shouldSuggest: boolean;
  }>;
  modelVersion: string;
  totalProcessingTime: number;
  averageConfidence: number;
}

export interface MLFeedbackRequest {
  transactionId: string;
  predictedCategoryId: string;
  actualCategoryId: string;
  userAction: 'accepted' | 'corrected' | 'rejected';
  confidence: number;
  description: string;
  merchant?: string;
  amountCents: number;
}

export interface MLFeedbackResponse {
  feedbackId: string;
  processed: boolean;
  modelWillRetrain: boolean;
  estimatedImpact: 'low' | 'medium' | 'high';
  message: string;
}

export interface MLInsights {
  userId: string;
  period: string;
  insights: Array<{
    type: 'spending_pattern' | 'category_trend' | 'anomaly' | 'suggestion';
    title: string;
    description: string;
    confidence: number;
    actionable: boolean;
    data?: Record<string, any>;
  }>;
  generatedAt: string;
  modelVersion: string;
}

// ML model status and health
export interface MLModelStatus {
  modelVersion: string;
  status: 'healthy' | 'degraded' | 'offline' | 'training';
  lastHealthCheck: string;
  performance: MLModelPerformance;
  issues?: string[];
  nextTrainingScheduled?: string;
}

// Configuration for ML behavior
export interface MLConfiguration {
  autoApplyThreshold: number;
  suggestionThreshold: number;
  minimumConfidenceThreshold: number;
  enableAutoApply: boolean;
  enableSuggestions: boolean;
  enableBatchProcessing: boolean;
  maxAlternativeCategories: number;
  feedbackLearningEnabled: boolean;
  retrainingFrequency: 'daily' | 'weekly' | 'monthly';
}