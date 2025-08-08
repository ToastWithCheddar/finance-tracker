from celery import Celery
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List
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

# Global production orchestrator
production_orchestrator = None

# Initialize ML classifier on worker startup
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks and initialize production ML system"""
    global production_orchestrator
    
    try:
        # Create production orchestrator with model variants
        models_config = [
            {'name': 'sentence_transformer', 'type': 'base'},
            {'name': 'onnx_optimized', 'type': 'onnx'},
            {'name': 'quantized', 'type': 'onnx_quantized'}
        ]
        
        production_orchestrator = create_production_orchestrator(
            models_config=models_config,
            monitoring_enabled=True,
            ab_testing_enabled=True
        )
        
        # Initialize production system asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(production_orchestrator.initialize_production())
        loop.close()
        
        logger.info("🚀 Production ML system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize production ML system: {e}")
        # Fallback to basic classifier
        try:
            classifier.load_model()
            classifier.initialize_category_prototypes()
            
            # Try to load existing prototypes
            try:
                classifier.load_prototypes('models/category_prototypes.pkl')
            except:
                logger.info("No existing prototypes found, using defaults")
            
            logger.info("Fallback to basic ML Classification service")
        except Exception as fallback_error:
            logger.error(f"Fallback initialization also failed: {fallback_error}")

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
        results = classifier.batch_classify(transactions)
        logger.info(f"Batch classified {len(transactions)} transactions")
        return results
        
    except Exception as e:
        logger.error(f"Batch classification failed: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)

@app.task
def collect_user_feedback(feedback_data: Dict):
    """Collect user feedback for model improvement with production tracking"""
    global production_orchestrator
    
    try:
        if production_orchestrator:
            # Use production orchestrator for feedback
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            loop.run_until_complete(
                production_orchestrator.submit_feedback(
                    transaction_id=feedback_data['transaction_id'],
                    predicted_category=feedback_data['predicted_category'],
                    actual_category=feedback_data['actual_category'],
                    user_id=feedback_data['user_id']
                )
            )
            
            loop.close()
        
        # Also collect in basic classifier for compatibility
        classifier.collect_feedback(
            transaction_id=feedback_data['transaction_id'],
            predicted_category=feedback_data['predicted_category'],
            actual_category=feedback_data['actual_category'],
            user_id=feedback_data['user_id']
        )
        
        logger.info(f"Feedback collected for transaction {feedback_data['transaction_id']}")
        return {"status": "feedback_collected"}
        
    except Exception as e:
        logger.error(f"Failed to collect feedback: {e}")
        return {"status": "error", "message": str(e)}

@app.task
def update_model_from_feedback(user_id: str):
    """Update model prototypes based on user feedback"""
    try:
        classifier.update_from_feedback(user_id)
        
        # Save updated prototypes
        classifier.save_prototypes('models/category_prototypes.pkl')
        
        logger.info(f"Model updated from feedback for user {user_id}")
        return {"status": "model_updated"}
        
    except Exception as e:
        logger.error(f"Failed to update model: {e}")
        return {"status": "error", "message": str(e)}

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