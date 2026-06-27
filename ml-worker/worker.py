from celery import Celery
from celery.signals import worker_ready, worker_init, task_prerun, task_postrun
import structlog
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
from production_orchestrator import ProductionOrchestrator
from model_monitoring import model_monitor
from ab_testing_framework import ab_framework

try:
    from prometheus_client import start_http_server as _prom_start_http_server
except Exception:  # pragma: no cover
    _prom_start_http_server = None

# Configure structured logging via shared config (ML-LOG-001).
try:
    from app.logging_config import configure_logging  # type: ignore
except Exception:  # pragma: no cover
    try:
        from logging_config import configure_logging  # type: ignore
    except Exception:
        def configure_logging(_name: str) -> None:  # type: ignore
            return None
configure_logging("ml-worker")
logger = logging.getLogger(__name__)

# Propagate request_id from backend Celery callsite (apply_async(headers={...}))
# into structlog contextvars so every ml-worker log line carries the same id.
@task_prerun.connect
def _bind_request_id(sender=None, task_id=None, task=None, **kwargs):
    request_id = None
    try:
        headers = getattr(task.request, "headers", None) or {}
        request_id = headers.get("X-Request-ID") or headers.get("x-request-id")
    except Exception:
        request_id = None
    if not request_id:
        request_id = task_id or "no-request-id"
    structlog.contextvars.bind_contextvars(request_id=request_id, task_name=getattr(task, "name", "?"))


@task_postrun.connect
def _unbind_request_id(sender=None, task_id=None, task=None, **kwargs):
    try:
        structlog.contextvars.unbind_contextvars("request_id", "task_name")
    except Exception:
        pass


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

# Module-level singletons. Each Celery prefork child gets its own copy
# (Celery prefork model: workers fork after import, signals fire post-fork).
# ML-PR-003: one event loop per worker child instead of per task.
production_orchestrator: "ProductionOrchestrator | None" = None
_worker_loop: "asyncio.AbstractEventLoop | None" = None


def _is_light_startup() -> bool:
    """Light startup is now opt-in via env (ML_LIGHT_STARTUP=1).

    Default: heavy startup (orchestrator init) so the live ONNX path is wired.
    """
    return os.getenv("ML_LIGHT_STARTUP", "0") == "1"


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
        logger.info("[ok] Background ONNX export complete")
    except Exception as e:
        logger.warning(f"Background ONNX export skipped due to error: {e}")


# ML-PR-003: allocate a single event loop per Celery prefork child at
# worker_init (post-fork, pre-task). Each task reuses this loop instead of
# instantiating a new one per call. Caveat: Celery prefork forks one
# child per --concurrency unit; each child gets its own loop. Threaded
# execution pools are not supported by this design (would need a
# loop-running thread).
@worker_init.connect
def _init_worker_loop_and_metrics(sender=None, **kwargs):
    global _worker_loop
    try:
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.info("worker event loop initialized")
    except Exception as e:
        logger.error(f"failed to init worker event loop: {e}")
        _worker_loop = None

    # Start Prometheus on a non-conflicting port (backend uses :8000).
    # Wrap in try/except — port-in-use must not crash the worker.
    if _prom_start_http_server is not None:
        port = int(os.getenv("ML_METRICS_PORT", "8002"))
        try:
            _prom_start_http_server(port)
            logger.info(f"ml-worker prometheus metrics on port {port}")
        except OSError as e:
            logger.warning(f"prometheus port {port} unavailable: {e}")
        except Exception as e:
            logger.warning(f"prometheus start failed: {e}")


# Initialize ML classifier on worker startup
@worker_ready.connect
def setup_worker_tasks(sender, **kwargs):
    """Setup periodic tasks and initialize ML system.

    Default path (Section F, ML-PR-001): instantiate ProductionOrchestrator
    and call initialize_production() synchronously via asyncio.run() once.
    Failures degrade to the PyTorch fallback rather than crashing the
    worker. Set ML_LIGHT_STARTUP=1 to skip the orchestrator entirely.
    """
    global production_orchestrator

    if not _is_light_startup():
        try:
            production_orchestrator = ProductionOrchestrator()
            asyncio.run(production_orchestrator.initialize_production())
            logger.info(
                "production orchestrator initialized: %s",
                production_orchestrator.health(),
            )
        except Exception as e:
            logger.error(
                "production orchestrator init failed; degrading to PyTorch fallback: %s",
                e,
                exc_info=True,
            )
            production_orchestrator = None

    # Light startup / fallback path: prime basic classifier so the PyTorch
    # fallback is always hot regardless of orchestrator state.
    if _is_light_startup() or production_orchestrator is None:
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
            logger.info("[ok] Light ML startup complete - model ready for inference")
            return
        except Exception as e:
            logger.error(f"Light startup failed: {e}", exc_info=True)

async def _classify_async(transaction_data: Dict) -> Dict:
    """Live inference path. Tries ONNX-INT8 via OptimizedInferenceEngine,
    falls back to PyTorch via TransactionClassifier on any failure or when
    the orchestrator is not initialized. (ML-PR-001 / ML-PERF-001)
    """
    global production_orchestrator

    description = transaction_data.get('description', '') or ''
    merchant = transaction_data.get('merchant')
    text = f"{merchant} {description}".strip() if merchant else description

    # Path 1: optimized ONNX-INT8 engine via orchestrator.
    if production_orchestrator is not None and getattr(
        production_orchestrator, "is_initialized", False
    ):
        try:
            engine = production_orchestrator.optimized_engine
            res = await engine.predict(text)
            logger.info(
                "ml.classify served by optimized_engine",
                extra={
                    "path": "optimized",
                    "backend": res.get("backend"),
                    "label": res["label"],
                    "score": res["score"],
                    "latency_ms": res["latency_ms"],
                },
            )
            return {
                'predicted_category': res['label'],
                'confidence': float(res['score']),
                'confidence_level': res['confidence_level'],
                'inference_time_ms': float(res['latency_ms']),
                'model_version': getattr(engine, 'model_version', 'optimized'),
                'all_similarities': res.get('all_similarities', {}),
                'transaction_id': transaction_data.get('id'),
                'inference_path': 'optimized',
            }
        except Exception as opt_err:
            logger.warning(
                "optimized_engine.predict failed; falling back to PyTorch: %s",
                opt_err,
            )

    # Path 2: PyTorch fallback via the basic classifier.
    result = classifier.classify_transaction(
        description=description,
        amount=transaction_data.get('amount'),
        merchant=merchant,
    )
    result['transaction_id'] = transaction_data.get('id')
    result['inference_path'] = 'pytorch_fallback'
    logger.info(
        "ml.classify served by pytorch fallback",
        extra={
            "path": "pytorch_fallback",
            "label": result.get('predicted_category'),
            "confidence": result.get('confidence'),
        },
    )
    return result


@app.task(bind=True, max_retries=3)
def classify_transaction(self, transaction_data: Dict):
    """Classify a single transaction using the live ONNX path with PyTorch
    fallback. ML-PR-003: uses the worker-shared event loop.
    """
    global _worker_loop
    try:
        loop = _worker_loop
        if loop is None or loop.is_closed():
            # Defensive: should not happen post worker_init, but guard anyway.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(_classify_async(transaction_data))
    except Exception as e:
        logger.error(
            f"Classification failed for transaction {transaction_data.get('id')}: {e}"
        )
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
        logger.info(f"[ok] Batch classified {batch_size} transactions in {processing_time:.2f}s ({processing_time/batch_size:.3f}s per transaction)")
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
