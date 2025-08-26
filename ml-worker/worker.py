from celery import Celery
from celery.signals import worker_ready
import os
import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, List
# Reduce HF tokenizers fork warnings and potential deadlocks in Celery prefork
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# Force CPU inference; prevents any accidental GPU selection if present
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from ml_classification_service import classifier
from production_orchestrator import create_production_orchestrator
from model_monitoring import model_monitor
from ab_testing_framework import ab_framework

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery('ml_worker')

# Configure Celery
app.conf.update(
    broker_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    result_backend=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Global production orchestrator (unused in light startup)
production_orchestrator = None

def _is_light_startup() -> bool:
    """Always use light startup to avoid heavy init paths."""
    return True


def _ensure_onnx_in_background():
    """Create minimal ONNX artifacts if missing, without blocking worker start.
    Generates base ONNX and dynamic-quantized variant. Skips benchmarks/static quant.
    """
    try:
        from onnx_converter import onnx_converter
        models_dir = "models/production"
        os.makedirs(models_dir, exist_ok=True)
        base_path = os.path.join(models_dir, "transaction_classifier.onnx")
        dyn_path = os.path.join(models_dir, "transaction_classifier_dynamic_q8.onnx")

        if os.path.exists(dyn_path) and os.path.exists(base_path):
            logger.info("ONNX artifacts already present; skipping generation")
            return

        logger.info("Starting background ONNX export (base + dynamic quantization)")
        # Load model on CPU and export
        onnx_converter.load_model()
        onnx_converter.export_to_onnx(base_path)
        onnx_converter.quantize_dynamic(base_path, dyn_path)
        logger.info("✅ Background ONNX export complete")
    except Exception as e:
        logger.warning(f"Background ONNX export skipped due to error: {e}")


# Initialize ML classifier on worker startup
@worker_ready.connect
def setup_worker_tasks(sender, **kwargs):
    """Setup periodic tasks and initialize ML system.
    In light startup, preload basic model/prototypes and skip heavy production init
    so the worker can accept tasks immediately.
    """
    global production_orchestrator

    # Light startup path: fast readiness, no heavy production init
    if _is_light_startup():
        try:
            models_dir = classifier._models_root()
            prototypes_path = os.path.join(models_dir, 'category_prototypes.pkl')
            
            # Ensure model is loaded and ready
            logger.info(f"Loading model from models directory: {models_dir}")
            classifier.load_model()
            
            if not classifier.sentence_model:
                raise ValueError("Failed to load sentence model")
            
            try:
                classifier.load_prototypes(prototypes_path)
                if not classifier.category_prototypes:
                    raise ValueError("Empty prototypes after load")
                logger.info(f"Loaded {len(classifier.category_prototypes)} prototypes from {prototypes_path}")
            except Exception as e:
                logger.info(f"No valid prototypes found ({e}); initializing defaults")
                classifier.initialize_category_prototypes()
                try:
                    os.makedirs(os.path.dirname(prototypes_path), exist_ok=True)
                    classifier.save_prototypes(prototypes_path)
                    logger.info(f"Saved {len(classifier.category_prototypes)} initial prototypes to {prototypes_path}")
                except Exception as save_err:
                    logger.warning(f"Could not save prototypes: {save_err}")

            # Skip creating production orchestrator to avoid heavy startup
            # Kick off minimal ONNX generation in the background
            threading.Thread(target=_ensure_onnx_in_background, daemon=True).start()
            logger.info("✅ Light ML startup complete - model ready for inference")
            return
        except Exception as e:
            logger.error(f"Light startup failed: {e}", exc_info=True)

@app.task(bind=True, max_retries=3)
def classify_transaction(self, transaction_data: Dict):
    """Classify a single transaction using production-optimized ML system"""
    global production_orchestrator
    
    try:
        if production_orchestrator:
            # Use production orchestrator with A/B testing and monitoring
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                production_orchestrator.classify_transaction(
                    description=transaction_data.get('description', ''),
                    amount=transaction_data.get('amount'),
                    merchant=transaction_data.get('merchant'),
                    user_id=transaction_data.get('user_id')
                )
            )
            
            loop.close()
            
            # Convert to dict format
            result_dict = {
                'predicted_category': result.predicted_category,
                'confidence': result.confidence,
                'confidence_level': result.confidence_level,
                'inference_time_ms': result.inference_time_ms,
                'model_version': result.model_version,
                'all_similarities': result.all_similarities,
                'transaction_id': transaction_data.get('id')
            }
            
            logger.info(f"Production classified transaction {transaction_data.get('id')}: "
                       f"{result.predicted_category} (confidence: {result.confidence:.3f}, "
                       f"time: {result.inference_time_ms:.1f}ms)")
            
            return result_dict
        
        else:
            # Fallback to basic classifier
            result = classifier.classify_transaction(
                description=transaction_data.get('description', ''),
                amount=transaction_data.get('amount'),
                merchant=transaction_data.get('merchant')
            )
            
            result['transaction_id'] = transaction_data.get('id')
            logger.info(f"Fallback classified transaction {transaction_data.get('id')}: {result['predicted_category']} (confidence: {result['confidence']:.3f})")
            
            return result
        
    except Exception as e:
        logger.error(f"Classification failed for transaction {transaction_data.get('id')}: {e}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)

@app.task(bind=True, max_retries=3)
def batch_classify_transactions(self, transactions: List[Dict]):
    """Classify multiple transactions in batch"""
    try:
        batch_size = len(transactions)
        logger.info(f"Starting batch classification for {batch_size} transactions")
        
        # Ensure model is loaded in worker process
        if not classifier.sentence_model:
            logger.info("Loading model in worker process...")
            classifier.load_model()
            
        if not classifier.category_prototypes:
            logger.info("Loading prototypes in worker process...")
            prototypes_path = 'models/category_prototypes.pkl'
            try:
                classifier.load_prototypes(prototypes_path)
            except Exception:
                classifier.initialize_category_prototypes()
        
        start_time = datetime.now()
        results = classifier.batch_classify(transactions)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"✅ Batch classified {batch_size} transactions in {processing_time:.2f}s ({processing_time/batch_size:.3f}s per transaction)")
        return results
        
    except Exception as e:
        logger.error(f"Batch classification failed for {len(transactions)} transactions: {e}", exc_info=True)
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)


@app.task
def add_category_example(category: str, example: str, user_id: str = None):
    """Add a new example to a category"""
    try:
        classifier.add_category_example(category, example, user_id)
        
        # Save updated prototypes
        classifier.save_prototypes('models/category_prototypes.pkl')
        
        logger.info(f"Added example to {category}: {example}")
        return {"status": "example_added"}
        
    except Exception as e:
        logger.error(f"Failed to add example: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def export_model_to_onnx():
    """Export the current model to ONNX format"""
    try:
        classifier.export_to_onnx('models/transaction_classifier.onnx')
        
        # Also quantize the model
        quantized_path = classifier.quantize_model('models/transaction_classifier.onnx')
        
        logger.info("Model exported and quantized successfully")
        return {
            "status": "exported",
            "onnx_path": "models/transaction_classifier.onnx",
            "quantized_path": quantized_path
        }
        
    except Exception as e:
        logger.error(f"Failed to export model: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def get_model_performance():
    """Get current model performance metrics"""
    try:
        performance = classifier.get_model_performance()
        logger.info(f"Model performance: {performance['accuracy']:.3f} accuracy")
        return performance
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def health_check():
    """Health check for the ML worker"""
    global production_orchestrator
    
    try:
        if production_orchestrator:
            # Production health check
            status = production_orchestrator.get_production_status()
            return {
                "status": "healthy" if status['is_production_ready'] else "degraded",
                "production_ready": status['is_production_ready'],
                "active_models": len(status['active_models']),
                "monitoring_enabled": status['monitoring_enabled'],
                "ab_testing_enabled": status['ab_testing_enabled'],
                "current_experiment": status['current_experiment']
            }
        else:
            # Basic health checks
            model_loaded = classifier.sentence_model is not None
            prototypes_loaded = len(classifier.category_prototypes) > 0
            
            return {
                "status": "healthy",
                "model_loaded": model_loaded,
                "prototypes_loaded": prototypes_loaded,
                "categories_count": len(classifier.category_prototypes),
                "model_version": classifier.model_version
            }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}

# New production-specific tasks
@app.task
def get_production_metrics():
    """Get comprehensive production metrics"""
    global production_orchestrator
    
    try:
        if production_orchestrator:
            return production_orchestrator.get_production_status()
        else:
            return {"status": "production_orchestrator_not_available"}
            
    except Exception as e:
        logger.error(f"Failed to get production metrics: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def generate_production_report():
    """Generate comprehensive production report"""
    global production_orchestrator
    
    try:
        if production_orchestrator:
            return production_orchestrator.generate_production_report()
        else:
            return {"status": "production_orchestrator_not_available"}
            
    except Exception as e:
        logger.error(f"Failed to generate production report: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def benchmark_production_models():
    """Run benchmark tests on all production models"""
    global production_orchestrator
    
    try:
        if production_orchestrator:
            results = {}
            for model_name, model_info in production_orchestrator.active_models.items():
                engine = model_info['engine']
                benchmark = engine.benchmark_performance(num_samples=200)
                results[model_name] = benchmark
            
            return {
                "status": "completed",
                "benchmarks": results,
                "timestamp": str(datetime.now())
            }
        else:
            return {"status": "production_orchestrator_not_available"}
            
    except Exception as e:
        logger.error(f"Failed to benchmark models: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def create_onnx_models():
    """Create optimized ONNX models with quantization"""
    try:
        from onnx_converter import onnx_converter
        
        # Create production models
        models_dir = "models/production"
        result = onnx_converter.create_production_models(models_dir)
        
        return {
            "status": "completed",
            "models": list(result['models'].keys()),
            "benchmarks": result['benchmarks'],
            "models_dir": models_dir
        }
        
    except Exception as e:
        logger.error(f"Failed to create ONNX models: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def get_ab_test_results():
    """Get A/B testing experiment results"""
    global production_orchestrator
    
    try:
        if production_orchestrator and production_orchestrator.current_experiment_id:
            experiment_id = production_orchestrator.current_experiment_id
            report = production_orchestrator.ab_framework.generate_experiment_report(experiment_id)
            return report
        else:
            return {"status": "no_active_experiment"}
            
    except Exception as e:
        logger.error(f"Failed to get A/B test results: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def optimize_for_production():
    """Apply all production optimizations"""
    global production_orchestrator
    
    try:
        if production_orchestrator:
            for model_name, model_info in production_orchestrator.active_models.items():
                engine = model_info['engine']
                engine.optimize_for_production()
            
            return {"status": "optimizations_applied"}
        else:
            # Fallback optimization
            classifier.sentence_model.eval()  # Ensure eval mode
            return {"status": "basic_optimization_applied"}
            
    except Exception as e:
        logger.error(f"Failed to optimize for production: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    app.start()
