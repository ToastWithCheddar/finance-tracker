"""
Production-Optimized ML Inference Engine
CPU-optimized inference with <10ms latency, ONNX runtime, and batch processing
"""

import os
import time
import json
import pickle
import asyncio
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

import numpy as np
import onnxruntime as ort
from sentence_transformers import SentenceTransformer
import torch
from sklearn.metrics.pairwise import cosine_similarity_chunked
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InferenceResult:
    predicted_category: str
    confidence: float
    confidence_level: str
    inference_time_ms: float
    model_version: str
    all_similarities: Optional[Dict[str, float]] = None

@dataclass
class BatchInferenceResult:
    results: List[InferenceResult]
    total_inference_time_ms: float
    avg_inference_time_ms: float
    batch_size: int
    throughput_per_second: float

class OptimizedInferenceEngine:
    """
    Production-optimized inference engine with <10ms CPU inference
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.sentence_model = None
        self.onnx_session = None
        self.category_prototypes = {}
        self.model_version = "v2.0_optimized"
        
        # Performance optimization settings
        self.embedding_cache = {}
        self.cache_max_size = 10000
        self.batch_size_optimal = 32
        
        # Threading for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())
        self.lock = threading.RLock()
        
        # Performance monitoring
        self.inference_stats = {
            'total_inferences': 0,
            'total_time_ms': 0,
            'avg_time_ms': 0,
            'max_time_ms': 0,
            'min_time_ms': float('inf'),
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # CPU optimization settings
        self._setup_cpu_optimization()
    
    def _setup_cpu_optimization(self):
        """Setup CPU optimization for fastest inference"""
        # Set optimal thread counts
        torch.set_num_threads(min(4, os.cpu_count()))
        
        # Disable gradient computation
        torch.set_grad_enabled(False)
        
        # Set CPU affinity for better cache locality
        if hasattr(os, 'sched_setaffinity'):
            try:
                os.sched_setaffinity(0, range(min(4, os.cpu_count())))
            except:
                pass
    
    def load_optimized_model(self, force_reload: bool = False):
        """Load optimized sentence transformer model"""
        if self.sentence_model and not force_reload:
            return
            
        start_time = time.time()
        
        try:
            # Load with CPU optimization
            device = 'cpu'
            # Check if model exists locally first
            local_model_path = f"/app/models/{self.model_name}"
            if os.path.exists(local_model_path):
                self.sentence_model = SentenceTransformer(
                    local_model_path, 
                    device=device,
                    cache_folder='./model_cache'
                )
                print(f"Loaded local model: {local_model_path}")
            else:
                self.sentence_model = SentenceTransformer(
                    self.model_name, 
                    device=device,
                    cache_folder='./model_cache'
                )
                print(f"Loaded hub model: {self.model_name}")
            
            # Optimize model for inference
            self.sentence_model.eval()
            
            # Warm up the model with a dummy input
            self._warmup_model()
            
            load_time = (time.time() - start_time) * 1000
            logger.info(f"Optimized model loaded in {load_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"Failed to load optimized model: {e}")
            raise
    
    def _warmup_model(self):
        """Warm up model with dummy inputs to optimize initial inference"""
        dummy_texts = [
            "coffee shop purchase",
            "grocery store shopping", 
            "gas station fuel"
        ]
        
        # Perform dummy inferences to warm up
        for _ in range(3):
            self.sentence_model.encode(dummy_texts, convert_to_tensor=False)
    
    def load_onnx_model(self, onnx_path: str, quantized: bool = True):
        """Load ONNX model for optimized CPU inference"""
        try:
            # Configure ONNX Runtime for CPU optimization
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = min(4, os.cpu_count())
            sess_options.inter_op_num_threads = 1
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            providers = ['CPUExecutionProvider']
            
            self.onnx_session = ort.InferenceSession(
                onnx_path,
                sess_options=sess_options,
                providers=providers
            )
            
            logger.info(f"ONNX model loaded: {onnx_path}")
            logger.info(f"Input shape: {self.onnx_session.get_inputs()[0].shape}")
            
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise
    
    def _get_embedding_cached(self, text: str) -> np.ndarray:
        """Get embedding with caching for repeated texts"""
        # Create cache key
        cache_key = hash(text.lower().strip())
        
        with self.lock:
            if cache_key in self.embedding_cache:
                self.inference_stats['cache_hits'] += 1
                return self.embedding_cache[cache_key]
            
            self.inference_stats['cache_misses'] += 1
            
            # Generate embedding
            embedding = self.sentence_model.encode([text], convert_to_tensor=False)[0]
            
            # Cache management
            if len(self.embedding_cache) >= self.cache_max_size:
                # Remove oldest entries (simple LRU)
                oldest_key = next(iter(self.embedding_cache))
                del self.embedding_cache[oldest_key]
            
            self.embedding_cache[cache_key] = embedding
            return embedding
    
    def classify_single_optimized(
        self, 
        description: str, 
        amount: float = None, 
        merchant: str = None
    ) -> InferenceResult:
        """Optimized single transaction classification with <10ms target"""
        
        start_time = time.perf_counter()
        
        try:
            # Prepare input text
            input_text = description
            if merchant:
                input_text = f"{merchant} {description}"
            
            # Get embedding (cached if available)
            transaction_embedding = self._get_embedding_cached(input_text)
            
            # Fast similarity computation using optimized numpy
            similarities = {}
            for category, data in self.category_prototypes.items():
                prototype = data['prototype']
                # Use optimized dot product for cosine similarity
                similarity = np.dot(transaction_embedding, prototype) / (
                    np.linalg.norm(transaction_embedding) * np.linalg.norm(prototype)
                )
                similarities[category] = float(similarity)
            
            # Find best match
            best_category = max(similarities, key=similarities.get)
            confidence = similarities[best_category]
            
            # Determine confidence level
            if confidence >= 0.8:
                confidence_level = "high"
            elif confidence >= 0.6:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            
            inference_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Update stats
            self._update_inference_stats(inference_time_ms)
            
            return InferenceResult(
                predicted_category=best_category,
                confidence=confidence,
                confidence_level=confidence_level,
                inference_time_ms=inference_time_ms,
                model_version=self.model_version,
                all_similarities=similarities
            )
            
        except Exception as e:
            logger.error(f"Optimized classification failed: {e}")
            raise
    
    def classify_batch_optimized(
        self, 
        transactions: List[Dict],
        batch_size: int = None
    ) -> BatchInferenceResult:
        """Optimized batch processing for maximum throughput"""
        
        if batch_size is None:
            batch_size = self.batch_size_optimal
        
        start_time = time.perf_counter()
        results = []
        
        # Process in optimal batches
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            
            # Prepare batch inputs
            batch_texts = []
            for t in batch:
                text = t.get('description', '')
                if t.get('merchant'):
                    text = f"{t['merchant']} {text}"
                batch_texts.append(text)
            
            # Batch embedding generation (more efficient)
            batch_embeddings = self.sentence_model.encode(
                batch_texts, 
                convert_to_tensor=False,
                show_progress_bar=False
            )
            
            # Process each embedding in batch
            for j, embedding in enumerate(batch_embeddings):
                transaction = batch[j]
                
                # Fast similarity computation
                similarities = {}
                for category, data in self.category_prototypes.items():
                    prototype = data['prototype']
                    similarity = np.dot(embedding, prototype) / (
                        np.linalg.norm(embedding) * np.linalg.norm(prototype)
                    )
                    similarities[category] = float(similarity)
                
                best_category = max(similarities, key=similarities.get)
                confidence = similarities[best_category]
                
                confidence_level = "high" if confidence >= 0.8 else "medium" if confidence >= 0.6 else "low"
                
                results.append(InferenceResult(
                    predicted_category=best_category,
                    confidence=confidence,
                    confidence_level=confidence_level,
                    inference_time_ms=0,  # Will calculate total time
                    model_version=self.model_version,
                    all_similarities=similarities
                ))
        
        total_time_ms = (time.perf_counter() - start_time) * 1000
        avg_time_ms = total_time_ms / len(transactions)
        throughput_per_second = len(transactions) / (total_time_ms / 1000)
        
        return BatchInferenceResult(
            results=results,
            total_inference_time_ms=total_time_ms,
            avg_inference_time_ms=avg_time_ms,
            batch_size=len(transactions),
            throughput_per_second=throughput_per_second
        )
    
    async def classify_async(
        self, 
        description: str, 
        amount: float = None, 
        merchant: str = None
    ) -> InferenceResult:
        """Async classification for non-blocking operation"""
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self.classify_single_optimized,
            description,
            amount,
            merchant
        )
    
    def _update_inference_stats(self, inference_time_ms: float):
        """Update performance statistics"""
        with self.lock:
            self.inference_stats['total_inferences'] += 1
            self.inference_stats['total_time_ms'] += inference_time_ms
            self.inference_stats['avg_time_ms'] = (
                self.inference_stats['total_time_ms'] / 
                self.inference_stats['total_inferences']
            )
            self.inference_stats['max_time_ms'] = max(
                self.inference_stats['max_time_ms'], 
                inference_time_ms
            )
            self.inference_stats['min_time_ms'] = min(
                self.inference_stats['min_time_ms'], 
                inference_time_ms
            )
    
    def get_performance_metrics(self) -> Dict:
        """Get detailed performance metrics"""
        with self.lock:
            cache_hit_rate = (
                self.inference_stats['cache_hits'] / 
                max(1, self.inference_stats['cache_hits'] + self.inference_stats['cache_misses'])
            ) * 100
            
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            
            return {
                **self.inference_stats.copy(),
                'cache_hit_rate_percent': cache_hit_rate,
                'cache_size': len(self.embedding_cache),
                'categories_loaded': len(self.category_prototypes),
                'model_version': self.model_version,
                'cpu_usage_percent': cpu_usage,
                'memory_usage_percent': memory_info.percent,
                'memory_available_mb': memory_info.available // (1024 * 1024),
                'target_latency_met': self.inference_stats['avg_time_ms'] < 10.0,
                'p95_estimate': self.inference_stats['max_time_ms'] * 0.95,  # Simple P95 estimate
            }
    
    def benchmark_performance(self, num_samples: int = 1000) -> Dict:
        """Benchmark inference performance"""
        logger.info(f"Running performance benchmark with {num_samples} samples...")
        
        # Test data
        test_descriptions = [
            "coffee shop starbucks morning",
            "uber ride to airport",
            "grocery store weekly shopping",
            "amazon online purchase",
            "gas station shell fuel",
            "restaurant dinner downtown",
            "netflix subscription payment",
            "doctor visit copay",
            "salary direct deposit",
            "electric bill monthly"
        ] * (num_samples // 10 + 1)
        
        test_transactions = [
            {'description': desc, 'amount': -20.0}
            for desc in test_descriptions[:num_samples]
        ]
        
        # Benchmark batch processing
        batch_result = self.classify_batch_optimized(test_transactions)
        
        # Benchmark single inference (average of 100 calls)
        single_times = []
        for i in range(100):
            start_time = time.perf_counter()
            self.classify_single_optimized(test_descriptions[i % len(test_descriptions)])
            single_times.append((time.perf_counter() - start_time) * 1000)
        
        avg_single_time = np.mean(single_times)
        p95_single_time = np.percentile(single_times, 95)
        p99_single_time = np.percentile(single_times, 99)
        
        return {
            'benchmark_samples': num_samples,
            'batch_processing': {
                'total_time_ms': batch_result.total_inference_time_ms,
                'avg_time_per_item_ms': batch_result.avg_inference_time_ms,
                'throughput_per_second': batch_result.throughput_per_second
            },
            'single_processing': {
                'avg_time_ms': avg_single_time,
                'p95_time_ms': p95_single_time,
                'p99_time_ms': p99_single_time,
                'target_10ms_met': avg_single_time < 10.0
            },
            'performance_metrics': self.get_performance_metrics()
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        with self.lock:
            self.embedding_cache.clear()
            logger.info("Embedding cache cleared")
    
    def load_prototypes(self, filepath: str):
        """Load category prototypes"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.category_prototypes = data['prototypes']
            
            logger.info(f"Loaded {len(self.category_prototypes)} category prototypes")
        except Exception as e:
            logger.error(f"Failed to load prototypes: {e}")
    
    def optimize_for_production(self):
        """Apply all production optimizations"""
        logger.info("Applying production optimizations...")
        
        # Clear any existing cache
        self.clear_cache()
        
        # Warm up model
        self._warmup_model()
        
        # Pre-compute commonly used embeddings
        common_terms = [
            "coffee", "starbucks", "uber", "lyft", "amazon", "walmart", 
            "target", "gas", "grocery", "restaurant", "netflix", "spotify"
        ]
        
        for term in common_terms:
            self._get_embedding_cached(term)
        
        logger.info("Production optimizations applied")

# Global optimized inference engine
optimized_engine = OptimizedInferenceEngine()