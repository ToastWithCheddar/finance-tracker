"""
Advanced ONNX Model Converter and Quantization System
Converts Sentence Transformers to optimized ONNX format with INT8 quantization
"""

import os
import time
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import tempfile

import torch
import torch.nn as nn
import onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, quantize_static, QuantType, QuantFormat
from onnxruntime.quantization.calibrate import CalibrationDataReader
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)

class CalibrationDataGenerator(CalibrationDataReader):
    """Generate calibration data for static quantization"""
    
    def __init__(self, tokenizer, calibration_texts: List[str], max_length: int = 128):
        self.tokenizer = tokenizer
        self.calibration_texts = calibration_texts
        self.max_length = max_length
        self.current_index = 0
        
    def get_next(self) -> Dict[str, np.ndarray]:
        if self.current_index >= len(self.calibration_texts):
            return None
        
        text = self.calibration_texts[self.current_index]
        self.current_index += 1
        
        # Tokenize input
        inputs = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='np'
        )
        
        return {
            'input_ids': inputs['input_ids'].astype(np.int64),
            'attention_mask': inputs['attention_mask'].astype(np.int64)
        }

class ONNXConverter:
    """Advanced ONNX converter with optimization and quantization"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.sentence_transformer = None
        
        # Calibration data for quantization
        self.calibration_texts = [
            "coffee shop purchase morning",
            "grocery store weekly shopping",
            "uber ride to downtown",
            "amazon online order delivery",
            "gas station fuel payment",
            "restaurant dinner with friends",
            "netflix monthly subscription",
            "doctor visit medical checkup",
            "salary direct deposit payment",
            "electric utility bill payment",
            "target shopping household items",
            "starbucks coffee and pastry",
            "walmart groceries and supplies",
            "shell gas station fill up",
            "lyft ride to airport",
            "spotify music streaming service",
            "pharmacy prescription pickup",
            "dentist cleaning appointment",
            "gym membership monthly fee",
            "parking garage downtown"
        ] * 10  # 200 samples for calibration
    
    def load_model(self):
        """Load the sentence transformer model"""
        try:
            # Check if model exists locally first
            local_model_path = f"/app/models/{self.model_name}"
            if os.path.exists(local_model_path):
                self.sentence_transformer = SentenceTransformer(local_model_path)
                print(f"Loaded local model for ONNX conversion: {local_model_path}")
            else:
                self.sentence_transformer = SentenceTransformer(self.model_name)
                print(f"Loaded hub model for ONNX conversion: {self.model_name}")
            
            # Extract the transformer model and tokenizer
            self.model = self.sentence_transformer[0].auto_model
            self.tokenizer = self.sentence_transformer[0].tokenizer
            
            # Set to eval mode
            self.model.eval()
            
            logger.info(f"Loaded model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def export_to_onnx(
        self, 
        output_path: str,
        max_length: int = 128,
        optimize: bool = True
    ) -> str:
        """Export model to ONNX format"""
        
        if not self.model or not self.tokenizer:
            self.load_model()
        
        try:
            # Create dummy inputs
            dummy_input_ids = torch.randint(0, 1000, (1, max_length), dtype=torch.long)
            dummy_attention_mask = torch.ones(1, max_length, dtype=torch.long)
            
            dummy_inputs = {
                'input_ids': dummy_input_ids,
                'attention_mask': dummy_attention_mask
            }
            
            # Export to ONNX
            torch.onnx.export(
                self.model,
                (dummy_inputs['input_ids'], dummy_inputs['attention_mask']),
                output_path,
                export_params=True,
                opset_version=14,
                do_constant_folding=True,
                input_names=['input_ids', 'attention_mask'],
                output_names=['last_hidden_state'],
                dynamic_axes={
                    'input_ids': {0: 'batch_size', 1: 'sequence_length'},
                    'attention_mask': {0: 'batch_size', 1: 'sequence_length'},
                    'last_hidden_state': {0: 'batch_size', 1: 'sequence_length'}
                }
            )
            
            # Optimize the ONNX model
            if optimize:
                self._optimize_onnx_model(output_path)
            
            logger.info(f"Model exported to ONNX: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"ONNX export failed: {e}")
            raise
    
    def _optimize_onnx_model(self, onnx_path: str):
        """Apply ONNX model optimizations"""
        try:
            from onnxruntime.tools import optimizer
            
            # Load and optimize
            optimized_path = onnx_path.replace('.onnx', '_optimized.onnx')
            
            # Apply graph optimizations
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.optimized_model_filepath = optimized_path
            
            # Create session to apply optimizations
            _ = ort.InferenceSession(onnx_path, sess_options)
            
            # Replace original with optimized version
            os.replace(optimized_path, onnx_path)
            
            logger.info("ONNX model optimized")
            
        except Exception as e:
            logger.warning(f"ONNX optimization failed: {e}")
    
    def quantize_dynamic(self, onnx_path: str, output_path: str = None) -> str:
        """Apply dynamic INT8 quantization"""
        
        if output_path is None:
            output_path = onnx_path.replace('.onnx', '_dynamic_quantized.onnx')
        
        try:
            quantize_dynamic(
                model_input=onnx_path,
                model_output=output_path,
                weight_type=QuantType.QInt8,
                per_channel=True,
                reduce_range=True,
                optimize_model=True
            )
            
            logger.info(f"Dynamic quantization completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Dynamic quantization failed: {e}")
            raise
    
    def quantize_static(self, onnx_path: str, output_path: str = None) -> str:
        """Apply static INT8 quantization with calibration data"""
        
        if output_path is None:
            output_path = onnx_path.replace('.onnx', '_static_quantized.onnx')
        
        try:
            # Create calibration data reader
            calibration_data_reader = CalibrationDataGenerator(
                self.tokenizer,
                self.calibration_texts
            )
            
            # Apply static quantization
            quantize_static(
                model_input=onnx_path,
                model_output=output_path,
                calibration_data_reader=calibration_data_reader,
                quant_format=QuantFormat.QOperator,
                per_channel=True,
                reduce_range=True,
                optimize_model=True
            )
            
            logger.info(f"Static quantization completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Static quantization failed: {e}")
            # Fallback to dynamic quantization
            logger.info("Falling back to dynamic quantization")
            return self.quantize_dynamic(onnx_path, output_path)
    
    def benchmark_models(
        self, 
        original_path: str, 
        quantized_paths: List[str],
        test_texts: List[str] = None
    ) -> Dict:
        """Benchmark different model versions"""
        
        if test_texts is None:
            test_texts = [
                "coffee shop purchase",
                "grocery store shopping", 
                "uber ride payment",
                "amazon online order",
                "gas station fuel"
            ] * 20  # 100 test samples
        
        results = {}
        
        # Test original PyTorch model
        if self.sentence_transformer:
            start_time = time.time()
            _ = self.sentence_transformer.encode(test_texts)
            pytorch_time = time.time() - start_time
            
            results['pytorch'] = {
                'inference_time_s': pytorch_time,
                'avg_time_per_sample_ms': (pytorch_time / len(test_texts)) * 1000,
                'throughput_per_second': len(test_texts) / pytorch_time
            }
        
        # Test ONNX models
        for model_path in [original_path] + quantized_paths:
            model_name = Path(model_path).stem
            
            try:
                # Create ONNX session
                sess_options = ort.SessionOptions()
                sess_options.intra_op_num_threads = 4
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                
                session = ort.InferenceSession(model_path, sess_options)
                
                # Prepare inputs
                inputs_list = []
                for text in test_texts:
                    inputs = self.tokenizer(
                        text,
                        max_length=128,
                        padding='max_length',
                        truncation=True,
                        return_tensors='np'
                    )
                    inputs_list.append({
                        'input_ids': inputs['input_ids'].astype(np.int64),
                        'attention_mask': inputs['attention_mask'].astype(np.int64)
                    })
                
                # Benchmark inference
                start_time = time.time()
                for inputs in inputs_list:
                    outputs = session.run(None, inputs)
                inference_time = time.time() - start_time
                
                # Get model size
                model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
                
                results[model_name] = {
                    'inference_time_s': inference_time,
                    'avg_time_per_sample_ms': (inference_time / len(test_texts)) * 1000,
                    'throughput_per_second': len(test_texts) / inference_time,
                    'model_size_mb': model_size_mb,
                    'model_path': model_path
                }
                
                logger.info(f"Benchmarked {model_name}: {results[model_name]['avg_time_per_sample_ms']:.2f}ms per sample")
                
            except Exception as e:
                logger.error(f"Failed to benchmark {model_path}: {e}")
                results[model_name] = {'error': str(e)}
        
        return results
    
    def validate_onnx_model(self, onnx_path: str, tolerance: float = 1e-3) -> bool:
        """Validate ONNX model against original PyTorch model"""
        
        try:
            # Load ONNX session
            session = ort.InferenceSession(onnx_path)
            
            # Test with sample input
            test_text = "coffee shop purchase morning"
            
            # Get PyTorch output
            pytorch_embedding = self.sentence_transformer.encode([test_text])[0]
            
            # Get ONNX output
            inputs = self.tokenizer(
                test_text,
                max_length=128,
                padding='max_length',
                truncation=True,
                return_tensors='np'
            )
            
            onnx_outputs = session.run(None, {
                'input_ids': inputs['input_ids'].astype(np.int64),
                'attention_mask': inputs['attention_mask'].astype(np.int64)
            })
            
            # Extract embeddings from ONNX output (mean pooling)
            last_hidden_state = onnx_outputs[0]
            attention_mask = inputs['attention_mask']
            
            # Mean pooling
            input_mask_expanded = np.broadcast_to(
                attention_mask.unsqueeze(-1), last_hidden_state.shape
            )
            sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
            sum_mask = np.sum(input_mask_expanded, axis=1)
            onnx_embedding = sum_embeddings / np.maximum(sum_mask, 1e-9)
            onnx_embedding = onnx_embedding[0]  # Remove batch dimension
            
            # Compare embeddings
            diff = np.mean(np.abs(pytorch_embedding - onnx_embedding))
            
            if diff < tolerance:
                logger.info(f"ONNX model validation passed (diff: {diff:.6f})")
                return True
            else:
                logger.warning(f"ONNX model validation failed (diff: {diff:.6f} > {tolerance})")
                return False
                
        except Exception as e:
            logger.error(f"ONNX model validation error: {e}")
            return False
    
    def create_production_models(self, output_dir: str) -> Dict[str, str]:
        """Create all production model variants"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        if not self.model or not self.tokenizer:
            self.load_model()
        
        model_paths = {}
        
        try:
            # 1. Export base ONNX model
            base_onnx_path = os.path.join(output_dir, "transaction_classifier.onnx")
            self.export_to_onnx(base_onnx_path)
            model_paths['base'] = base_onnx_path
            
            # Validate base model
            if not self.validate_onnx_model(base_onnx_path):
                logger.warning("Base ONNX model validation failed")
            
            # 2. Create dynamic quantized version
            dynamic_path = os.path.join(output_dir, "transaction_classifier_dynamic_q8.onnx")
            self.quantize_dynamic(base_onnx_path, dynamic_path)
            model_paths['dynamic_quantized'] = dynamic_path
            
            # 3. Create static quantized version
            static_path = os.path.join(output_dir, "transaction_classifier_static_q8.onnx")
            self.quantize_static(base_onnx_path, static_path)
            model_paths['static_quantized'] = static_path
            
            # 4. Benchmark all models
            benchmark_results = self.benchmark_models(
                base_onnx_path,
                [dynamic_path, static_path]
            )
            
            # Save benchmark results
            import json
            benchmark_path = os.path.join(output_dir, "benchmark_results.json")
            with open(benchmark_path, 'w') as f:
                json.dump(benchmark_results, f, indent=2)
            
            logger.info(f"Created production models in: {output_dir}")
            logger.info(f"Model paths: {model_paths}")
            
            return {
                'models': model_paths,
                'benchmarks': benchmark_results,
                'benchmark_file': benchmark_path
            }
            
        except Exception as e:
            logger.error(f"Failed to create production models: {e}")
            raise

# Global converter instance
onnx_converter = ONNXConverter()