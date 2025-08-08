"""
Production ML Orchestrator
Integrates optimization, monitoring, A/B testing, and ONNX deployment
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
import threading
import asyncio

from optimized_inference_engine import OptimizedInferenceEngine, InferenceResult
from onnx_converter import ONNXConverter
from model_monitoring import ModelMonitor
from ab_testing_framework import ABTestingFramework, ModelVariant, ExperimentConfig, TrafficSplitStrategy

logger = logging.getLogger(__name__)

@dataclass
class ProductionConfig:
    """Production deployment configuration"""
    model_variants: List[Dict[str, Any]]
    default_model_path: str
    monitoring_enabled: bool = True
    ab_testing_enabled: bool = True
    performance_targets: Dict[str, float] = None
    deployment_strategy: str = "blue_green"  # blue_green, canary, rolling
    
class ProductionOrchestrator:
    """
    Production ML orchestrator that manages model deployment,
    optimization, monitoring, and A/B testing
    """
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        
        # Core components
        self.inference_engine = OptimizedInferenceEngine()
        self.onnx_converter = ONNXConverter()
        self.model_monitor = ModelMonitor() if config.monitoring_enabled else None
        self.ab_framework = ABTestingFramework() if config.ab_testing_enabled else None
        
        # Model management
        self.active_models: Dict[str, Any] = {}
        self.model_performance: Dict[str, Dict] = {}
        
        # Production state
        self.is_production_ready = False
        self.current_experiment_id = None
        
        # Default performance targets
        self.performance_targets = config.performance_targets or {
            'max_inference_time_ms': 10.0,
            'min_accuracy': 0.85,
            'max_error_rate': 0.05,
            'min_throughput_per_second': 100
        }
        
        # Thread safety
        self.lock = threading.RLock()
    
    async def initialize_production(self):
        """Initialize production deployment"""
        
        logger.info("Initializing production ML system...")
        
        try:
            # 1. Load and optimize models
            await self._setup_models()
            
            # 2. Start monitoring if enabled
            if self.model_monitor:
                self.model_monitor.start_monitoring()
                logger.info("Model monitoring started")
            
            # 3. Run performance benchmarks
            await self._run_initial_benchmarks()
            
            # 4. Setup A/B testing if enabled
            if self.ab_framework:
                await self._setup_ab_testing()
                logger.info("A/B testing framework initialized")
            
            # 5. Validate production readiness
            self.is_production_ready = await self._validate_production_readiness()
            
            if self.is_production_ready:
                logger.info("🚀 Production ML system ready!")
            else:
                logger.warning("⚠️ Production readiness checks failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize production system: {e}")
            raise
    
    async def _setup_models(self):
        """Setup and optimize all model variants"""
        
        logger.info("Setting up model variants...")
        
        # Load base model
        self.inference_engine.load_optimized_model()
        self.inference_engine.load_prototypes('models/category_prototypes.pkl')
        
        # Create ONNX variants
        models_dir = "models/production"
        os.makedirs(models_dir, exist_ok=True)
        
        # Generate optimized ONNX models
        production_models = self.onnx_converter.create_production_models(models_dir)
        
        logger.info(f"Created production models: {list(production_models['models'].keys())}")
        
        # Load ONNX models for inference
        for model_type, model_path in production_models['models'].items():
            try:
                # Create separate inference engine for each variant
                if model_type in ['dynamic_quantized', 'static_quantized']:
                    engine = OptimizedInferenceEngine()
                    engine.load_onnx_model(model_path)
                    engine.load_prototypes('models/category_prototypes.pkl')
                    
                    self.active_models[model_type] = {
                        'engine': engine,
                        'path': model_path,
                        'type': model_type,
                        'benchmarks': production_models['benchmarks'].get(model_type, {})
                    }
                    
                    logger.info(f"Loaded {model_type} model: {model_path}")
            
            except Exception as e:
                logger.error(f"Failed to load {model_type} model: {e}")
        
        # Set default model
        self.active_models['default'] = {
            'engine': self.inference_engine,
            'path': self.config.default_model_path,
            'type': 'sentence_transformer',
            'benchmarks': {}
        }
    
    async def _run_initial_benchmarks(self):
        """Run performance benchmarks on all models"""
        
        logger.info("Running initial performance benchmarks...")
        
        for model_name, model_info in self.active_models.items():
            engine = model_info['engine']
            
            try:
                # Run benchmark
                benchmark_results = engine.benchmark_performance(num_samples=500)
                
                self.model_performance[model_name] = {
                    'benchmark_results': benchmark_results,
                    'meets_targets': self._check_performance_targets(benchmark_results),
                    'last_updated': datetime.now().isoformat()
                }
                
                logger.info(f"Benchmark {model_name}: "
                          f"avg {benchmark_results['single_processing']['avg_time_ms']:.1f}ms, "
                          f"targets met: {self.model_performance[model_name]['meets_targets']}")
                
            except Exception as e:
                logger.error(f"Benchmark failed for {model_name}: {e}")
                self.model_performance[model_name] = {
                    'benchmark_results': {},
                    'meets_targets': False,
                    'error': str(e),
                    'last_updated': datetime.now().isoformat()
                }
    
    def _check_performance_targets(self, benchmark_results: Dict) -> bool:
        """Check if benchmark results meet performance targets"""
        
        single_proc = benchmark_results.get('single_processing', {})
        batch_proc = benchmark_results.get('batch_processing', {})
        
        checks = [
            single_proc.get('avg_time_ms', float('inf')) <= self.performance_targets['max_inference_time_ms'],
            single_proc.get('target_10ms_met', False),
            batch_proc.get('throughput_per_second', 0) >= self.performance_targets['min_throughput_per_second']
        ]
        
        return all(checks)
    
    async def _setup_ab_testing(self):
        """Setup A/B testing experiments"""
        
        if not self.ab_framework:
            return
        
        # Create A/B test variants from available models
        variants = []
        
        for model_name, model_info in self.active_models.items():
            if model_name == 'default':
                continue
                
            benchmarks = self.model_performance.get(model_name, {}).get('benchmark_results', {})
            meets_targets = self.model_performance.get(model_name, {}).get('meets_targets', False)
            
            if meets_targets:
                variants.append(ModelVariant(
                    name=model_name,
                    model_path=model_info['path'],
                    model_version=f"{model_name}_v1.0",
                    weight=1.0 / max(1, len(self.active_models) - 1),  # Equal split
                    description=f"Optimized {model_info['type']} model",
                    config={'benchmarks': benchmarks}
                ))
        
        if len(variants) >= 2:
            # Create experiment
            experiment_config = ExperimentConfig(
                experiment_id=f"production_ab_test_{int(time.time())}",
                name="Production Model Comparison",
                description="Compare optimized model variants in production",
                variants=variants,
                traffic_split_strategy=TrafficSplitStrategy.USER_ID_HASH,
                start_time=datetime.now(),
                end_time=None,  # Run indefinitely
                success_metrics=['accuracy', 'inference_time', 'confidence'],
                minimum_sample_size=1000,
                guard_rails={
                    'min_accuracy': 0.75,
                    'max_inference_time_ms': 15.0
                }
            )
            
            self.current_experiment_id = self.ab_framework.create_experiment(experiment_config)
            self.ab_framework.start_experiment(self.current_experiment_id)
            
            logger.info(f"Started A/B test: {self.current_experiment_id}")
        else:
            logger.warning("Insufficient model variants for A/B testing")
    
    async def _validate_production_readiness(self) -> bool:
        """Validate system is ready for production"""
        
        checks = []
        
        # Check at least one model meets performance targets
        has_production_ready_model = any(
            perf.get('meets_targets', False) 
            for perf in self.model_performance.values()
        )
        checks.append(('performance_targets', has_production_ready_model))
        
        # Check monitoring is working
        if self.model_monitor:
            health = self.model_monitor.get_performance_metrics()
            monitoring_healthy = len(health) > 0
            checks.append(('monitoring', monitoring_healthy))
        else:
            checks.append(('monitoring', True))  # Disabled
        
        # Check models loaded successfully
        models_loaded = len(self.active_models) > 0
        checks.append(('models_loaded', models_loaded))
        
        # Check inference engine
        try:
            test_result = self.inference_engine.classify_single_optimized(
                "test transaction coffee shop", 5.0
            )
            inference_working = test_result.inference_time_ms > 0
            checks.append(('inference_working', inference_working))
        except:
            checks.append(('inference_working', False))
        
        # Log check results
        for check_name, passed in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"Production check {check_name}: {status}")
        
        return all(passed for _, passed in checks)
    
    async def classify_transaction(
        self, 
        description: str,
        amount: float = None,
        merchant: str = None,
        user_id: str = None
    ) -> InferenceResult:
        """
        Production transaction classification with A/B testing and monitoring
        """
        
        start_time = time.perf_counter()
        
        try:
            # Determine which model to use
            selected_model_name = 'default'
            
            if self.ab_framework and self.current_experiment_id:
                # A/B testing variant assignment
                variant = self.ab_framework.assign_variant(
                    self.current_experiment_id,
                    user_id=user_id
                )
                
                if variant and variant.name in self.active_models:
                    selected_model_name = variant.name
            
            # Get the selected model
            model_info = self.active_models[selected_model_name]
            engine = model_info['engine']
            
            # Perform inference
            result = engine.classify_single_optimized(description, amount, merchant)
            
            # Record monitoring metrics
            if self.model_monitor:
                self.model_monitor.record_inference(
                    inference_time_ms=result.inference_time_ms,
                    predicted_category=result.predicted_category,
                    confidence=result.confidence,
                    confidence_level=result.confidence_level,
                    model_version=f"{selected_model_name}_{result.model_version}"
                )
            
            # Record A/B test result
            if self.ab_framework and self.current_experiment_id:
                self.ab_framework.record_result(
                    experiment_id=self.current_experiment_id,
                    variant_name=selected_model_name,
                    user_id=user_id,
                    prediction=result.predicted_category,
                    confidence=result.confidence,
                    inference_time_ms=result.inference_time_ms
                )
            
            # Add production metadata
            result.model_version = f"production_{selected_model_name}_{result.model_version}"
            
            return result
            
        except Exception as e:
            # Record error
            if self.model_monitor:
                self.model_monitor.record_error(
                    error_type="inference_error",
                    model_version=f"production_{selected_model_name}",
                    details=str(e)
                )
            
            logger.error(f"Production inference failed: {e}")
            raise
    
    async def submit_feedback(
        self, 
        transaction_id: str,
        predicted_category: str,
        actual_category: str,
        user_id: str = None
    ):
        """Submit user feedback for model improvement"""
        
        is_correct = predicted_category == actual_category
        
        # Update monitoring metrics
        if self.model_monitor:
            # This would require tracking transaction ID to model version mapping
            # For now, we'll use the current model
            self.model_monitor.record_inference(
                inference_time_ms=0,  # Not available for feedback
                predicted_category=predicted_category,
                confidence=0.0,  # Not available for feedback
                confidence_level="unknown",
                model_version="production_feedback",
                is_correct=is_correct
            )
        
        # Update A/B test results if applicable
        if self.ab_framework and self.current_experiment_id:
            # Find the result to update
            results = self.ab_framework.results[self.current_experiment_id]
            for result in reversed(results):
                if (result.user_id == user_id and 
                    result.prediction == predicted_category):
                    result.is_correct = is_correct
                    break
    
    def get_production_status(self) -> Dict[str, Any]:
        """Get comprehensive production system status"""
        
        status = {
            'is_production_ready': self.is_production_ready,
            'active_models': {
                name: {
                    'type': info['type'],
                    'path': info['path'],
                    'performance': self.model_performance.get(name, {})
                }
                for name, info in self.active_models.items()
            },
            'performance_targets': self.performance_targets,
            'current_experiment': self.current_experiment_id,
            'monitoring_enabled': self.config.monitoring_enabled,
            'ab_testing_enabled': self.config.ab_testing_enabled
        }
        
        # Add monitoring metrics
        if self.model_monitor:
            status['monitoring_metrics'] = self.model_monitor.get_performance_metrics()
        
        # Add A/B testing status
        if self.ab_framework and self.current_experiment_id:
            status['experiment_status'] = self.ab_framework.experiment_status.get(
                self.current_experiment_id, 'unknown'
            ).value
        
        return status
    
    def generate_production_report(self) -> Dict[str, Any]:
        """Generate comprehensive production report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_status': self.get_production_status(),
            'model_benchmarks': self.model_performance,
            'recommendations': []
        }
        
        # A/B test results
        if self.ab_framework and self.current_experiment_id:
            ab_report = self.ab_framework.generate_experiment_report(self.current_experiment_id)
            report['ab_test_results'] = ab_report
            
            # Add A/B test recommendations
            if 'recommendations' in ab_report:
                report['recommendations'].extend(ab_report['recommendations'])
        
        # Performance recommendations
        for model_name, perf in self.model_performance.items():
            if not perf.get('meets_targets', False):
                report['recommendations'].append(
                    f"Model {model_name} does not meet performance targets. "
                    f"Consider optimization or replacement."
                )
        
        return report
    
    async def shutdown(self):
        """Graceful shutdown of production system"""
        
        logger.info("Shutting down production ML system...")
        
        # Stop A/B test
        if self.ab_framework and self.current_experiment_id:
            self.ab_framework.stop_experiment(self.current_experiment_id, "system_shutdown")
        
        # Stop monitoring
        if self.model_monitor:
            self.model_monitor.stop_monitoring()
        
        logger.info("Production ML system shutdown complete")

# Usage example and factory function
def create_production_orchestrator(
    models_config: List[Dict],
    monitoring_enabled: bool = True,
    ab_testing_enabled: bool = True
) -> ProductionOrchestrator:
    """Factory function to create production orchestrator"""
    
    config = ProductionConfig(
        model_variants=models_config,
        default_model_path="models/sentence_transformer",
        monitoring_enabled=monitoring_enabled,
        ab_testing_enabled=ab_testing_enabled,
        performance_targets={
            'max_inference_time_ms': 10.0,
            'min_accuracy': 0.85,
            'max_error_rate': 0.05,
            'min_throughput_per_second': 100
        }
    )
    
    return ProductionOrchestrator(config)