"""
ML Classification Service for Transaction Categorization
Implements sentence transformers with few-shot learning and ONNX optimization
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import onnx
import onnxruntime as ort
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionClassifier:
    """
    Intelligent transaction categorization using sentence transformers
    with few-shot learning capabilities
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.sentence_model = None
        self.category_prototypes = {}
        self.user_feedback = {}
        self.scaler = StandardScaler()
        self.onnx_session = None
        self.model_version = "v1.0"
        
        # Categories with example transactions for few-shot learning
        self.default_categories = {
            "Food & Dining": [
                "coffee starbucks morning",
                "restaurant dinner downtown", 
                "grocery store weekly shopping",
                "fast food lunch break",
                "takeout pizza delivery"
            ],
            "Transportation": [
                "uber ride to airport",
                "gas station fuel up",
                "metro card monthly pass",
                "parking garage downtown",
                "taxi cab fare"
            ],
            "Shopping": [
                "amazon online purchase",
                "target household items",
                "clothing store new shirt",
                "electronics store headphones",
                "pharmacy health supplies"
            ],
            "Bills & Utilities": [
                "electric bill monthly payment",
                "water utility service",
                "phone bill cellular service",
                "internet service provider",
                "rent monthly payment"
            ],
            "Entertainment": [
                "movie theater tickets",
                "streaming service subscription",
                "concert venue tickets",
                "gym membership monthly",
                "book store purchase"
            ],
            "Healthcare": [
                "doctor visit copay",
                "pharmacy prescription",
                "dental cleaning appointment",
                "medical lab test",
                "health insurance premium"
            ],
            "Income": [
                "salary direct deposit",
                "freelance payment received",
                "investment dividend",
                "tax refund deposit",
                "bonus payment"
            ]
        }
        
    def load_model(self):
        """Load the sentence transformer model"""
        try:
            # Check if model exists locally first
            local_model_path = f"/app/models/{self.model_name}"
            if os.path.exists(local_model_path):
                logger.info(f"Loading local sentence transformer model: {local_model_path}")
                self.sentence_model = SentenceTransformer(local_model_path)
                logger.info("Local model loaded successfully")
            else:
                logger.info(f"Loading sentence transformer model from hub: {self.model_name}")
                self.sentence_model = SentenceTransformer(self.model_name)
                logger.info("Hub model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def initialize_category_prototypes(self, custom_categories: Optional[Dict[str, List[str]]] = None):
        """Initialize category prototypes using few-shot examples"""
        if not self.sentence_model:
            self.load_model()
            
        categories = custom_categories or self.default_categories
        
        logger.info("Initializing category prototypes...")
        for category, examples in categories.items():
            # Encode example transactions
            embeddings = self.sentence_model.encode(examples)
            # Create prototype as mean embedding
            prototype = np.mean(embeddings, axis=0)
            self.category_prototypes[category] = {
                'prototype': prototype,
                'examples': examples,
                'embedding_dim': len(prototype)
            }
        
        logger.info(f"Initialized {len(self.category_prototypes)} category prototypes")
    
    def add_category_example(self, category: str, example: str, user_id: Optional[str] = None):
        """Add a new example to a category and update prototype"""
        if not self.sentence_model:
            self.load_model()
            
        if category not in self.category_prototypes:
            self.category_prototypes[category] = {
                'prototype': None,
                'examples': [],
                'embedding_dim': 384  # Default for MiniLM
            }
        
        # Add example
        self.category_prototypes[category]['examples'].append(example)
        
        # Recompute prototype
        examples = self.category_prototypes[category]['examples']
        embeddings = self.sentence_model.encode(examples)
        prototype = np.mean(embeddings, axis=0)
        self.category_prototypes[category]['prototype'] = prototype
        
        logger.info(f"Added example to {category}: {example}")
    
    def classify_transaction(self, description: str, amount: float = None, 
                           merchant: str = None) -> Dict:
        """Classify a transaction using few-shot learning"""
        if not self.sentence_model or not self.category_prototypes:
            raise ValueError("Model not initialized. Call load_model() and initialize_category_prototypes() first.")
        
        # Prepare input text
        input_text = description
        if merchant:
            input_text = f"{merchant} {description}"
        
        # Encode transaction
        transaction_embedding = self.sentence_model.encode([input_text])[0]
        
        # Calculate similarities to all prototypes
        similarities = {}
        for category, data in self.category_prototypes.items():
            prototype = data['prototype']
            similarity = cosine_similarity([transaction_embedding], [prototype])[0][0]
            similarities[category] = similarity
        
        # Find best match
        best_category = max(similarities, key=similarities.get)
        confidence = similarities[best_category]
        
        # Apply confidence thresholds
        if confidence < 0.3:
            confidence_level = "low"
        elif confidence < 0.7:
            confidence_level = "medium"
        else:
            confidence_level = "high"
        
        return {
            'predicted_category': best_category,
            'confidence': float(confidence),
            'confidence_level': confidence_level,
            'all_similarities': {k: float(v) for k, v in similarities.items()},
            'model_version': self.model_version,
            'timestamp': datetime.now().isoformat()
        }
    
    def batch_classify(self, transactions: List[Dict]) -> List[Dict]:
        """Classify multiple transactions in batch"""
        results = []
        for transaction in transactions:
            result = self.classify_transaction(
                description=transaction.get('description', ''),
                amount=transaction.get('amount'),
                merchant=transaction.get('merchant')
            )
            result['transaction_id'] = transaction.get('id')
            results.append(result)
        
        return results
    
    def collect_feedback(self, transaction_id: str, predicted_category: str, 
                        actual_category: str, user_id: str):
        """Collect user feedback for model improvement"""
        feedback_entry = {
            'transaction_id': transaction_id,
            'predicted_category': predicted_category,
            'actual_category': actual_category,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        if user_id not in self.user_feedback:
            self.user_feedback[user_id] = []
        
        self.user_feedback[user_id].append(feedback_entry)
        logger.info(f"Collected feedback for transaction {transaction_id}")
    
    def update_from_feedback(self, user_id: str, min_feedback_count: int = 5):
        """Update category prototypes based on user feedback"""
        if user_id not in self.user_feedback:
            return
        
        feedback_data = self.user_feedback[user_id]
        
        # Group feedback by actual category
        category_corrections = {}
        for feedback in feedback_data:
            actual_cat = feedback['actual_category']
            if actual_cat not in category_corrections:
                category_corrections[actual_cat] = []
            category_corrections[actual_cat].append(feedback)
        
        # Update prototypes for categories with enough feedback
        for category, corrections in category_corrections.items():
            if len(corrections) >= min_feedback_count:
                # Get transaction descriptions from corrections
                # This would require fetching actual transaction data
                logger.info(f"Would update {category} with {len(corrections)} corrections")
    
    def export_to_onnx(self, output_path: str = "models/transaction_classifier.onnx"):
        """Export model to ONNX format for production deployment"""
        if not self.sentence_model:
            raise ValueError("Model not loaded")
        
        try:
            # Create dummy input for tracing
            dummy_input = torch.randn(1, 512)  # Max sequence length
            
            # Export the transformer model
            torch.onnx.export(
                self.sentence_model[0].auto_model,
                dummy_input,
                output_path,
                export_params=True,
                opset_version=11,
                do_constant_folding=True,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={
                    'input': {0: 'batch_size', 1: 'sequence'},
                    'output': {0: 'batch_size'}
                }
            )
            
            logger.info(f"Model exported to ONNX: {output_path}")
            
        except Exception as e:
            logger.error(f"ONNX export failed: {e}")
            # Fallback: save prototypes as numpy arrays
            self.save_prototypes(output_path.replace('.onnx', '_prototypes.pkl'))
    
    def quantize_model(self, model_path: str, quantized_path: str = None):
        """Apply INT8 quantization to ONNX model"""
        try:
            import onnxruntime.quantization as quantization
            
            if quantized_path is None:
                quantized_path = model_path.replace('.onnx', '_quantized.onnx')
            
            quantization.quantize_dynamic(
                model_path,
                quantized_path,
                weight_type=quantization.QuantType.QInt8
            )
            
            logger.info(f"Model quantized: {quantized_path}")
            return quantized_path
            
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return model_path
    
    def load_onnx_model(self, model_path: str):
        """Load ONNX model for inference"""
        try:
            self.onnx_session = ort.InferenceSession(model_path)
            logger.info(f"ONNX model loaded: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
    
    def save_prototypes(self, filepath: str):
        """Save category prototypes for persistence"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump({
                'prototypes': self.category_prototypes,
                'model_version': self.model_version,
                'model_name': self.model_name
            }, f)
        
        logger.info(f"Prototypes saved to {filepath}")
    
    def load_prototypes(self, filepath: str):
        """Load category prototypes from file"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.category_prototypes = data['prototypes']
                self.model_version = data.get('model_version', 'v1.0')
                
            logger.info(f"Prototypes loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load prototypes: {e}")
    
    def get_model_performance(self) -> Dict:
        """Calculate model performance metrics"""
        total_feedback = sum(len(feedback) for feedback in self.user_feedback.values())
        
        if total_feedback == 0:
            return {
                'total_predictions': 0,
                'total_feedback': 0,
                'accuracy': 0.0,
                'model_version': self.model_version
            }
        
        # Calculate accuracy from feedback
        correct_predictions = 0
        total_predictions = 0
        
        for user_feedback in self.user_feedback.values():
            for feedback in user_feedback:
                total_predictions += 1
                if feedback['predicted_category'] == feedback['actual_category']:
                    correct_predictions += 1
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        
        return {
            'total_predictions': total_predictions,
            'total_feedback': total_feedback,
            'correct_predictions': correct_predictions,
            'accuracy': accuracy,
            'model_version': self.model_version,
            'categories_count': len(self.category_prototypes),
            'users_with_feedback': len(self.user_feedback)
        }

# Global classifier instance
classifier = TransactionClassifier()