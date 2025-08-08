"""
Comprehensive Model Monitoring and Metrics System
Real-time monitoring, alerting, and performance tracking for ML models
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
from enum import Enum
import statistics

import numpy as np
import pandas as pd
from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
import psutil

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"  
    CRITICAL = "critical"

@dataclass
class ModelMetric:
    name: str
    value: float
    timestamp: datetime
    model_version: str
    labels: Dict[str, str] = None

@dataclass
class PerformanceSnapshot:
    timestamp: datetime
    model_version: str
    avg_inference_time_ms: float
    p95_inference_time_ms: float
    p99_inference_time_ms: float
    throughput_per_second: float
    accuracy: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    cache_hit_rate: float
    total_predictions: int
    
@dataclass
class Alert:
    level: AlertLevel
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float
    model_version: str

class ModelMonitor:
    """Comprehensive model monitoring and metrics collection"""
    
    def __init__(self, prometheus_port: int = 8000):
        self.prometheus_port = prometheus_port
        self.registry = CollectorRegistry()
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
        
        # In-memory metrics storage
        self.metrics_buffer = deque(maxlen=10000)
        self.performance_history = deque(maxlen=1000)
        self.alerts_history = deque(maxlen=500)
        
        # Real-time monitoring
        self.inference_times = deque(maxlen=1000)
        self.accuracy_buffer = deque(maxlen=100)
        self.error_count = 0
        self.total_requests = 0
        
        # Alert thresholds
        self.alert_thresholds = {
            'inference_time_ms': {'warning': 15.0, 'critical': 25.0},
            'error_rate': {'warning': 0.05, 'critical': 0.10},
            'accuracy': {'warning': 0.80, 'critical': 0.70},
            'memory_usage_mb': {'warning': 1024, 'critical': 2048},
            'cpu_usage_percent': {'warning': 80.0, 'critical': 95.0},
            'cache_hit_rate': {'warning': 0.70, 'critical': 0.50}
        }
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Background monitoring thread
        self.monitoring_thread = None
        self.monitoring_active = False
        
        # Model performance tracking
        self.model_versions = set()
        self.current_model_version = "unknown"
        
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        
        self.prom_inference_time = Histogram(
            'ml_inference_duration_seconds',
            'Time spent on ML inference',
            ['model_version', 'category'],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )
        
        self.prom_predictions_total = Counter(
            'ml_predictions_total',
            'Total number of predictions made',
            ['model_version', 'confidence_level'],
            registry=self.registry
        )
        
        self.prom_accuracy_gauge = Gauge(
            'ml_model_accuracy',
            'Current model accuracy',
            ['model_version'],
            registry=self.registry
        )
        
        self.prom_memory_usage = Gauge(
            'ml_memory_usage_bytes',
            'Memory usage in bytes',
            ['model_version'],
            registry=self.registry
        )
        
        self.prom_cpu_usage = Gauge(
            'ml_cpu_usage_percent',
            'CPU usage percentage',
            ['model_version'],
            registry=self.registry
        )
        
        self.prom_cache_hit_rate = Gauge(
            'ml_cache_hit_rate',
            'Cache hit rate',
            ['model_version'],
            registry=self.registry
        )
        
        self.prom_error_rate = Gauge(
            'ml_error_rate',
            'Error rate',
            ['model_version'],
            registry=self.registry
        )
        
    def start_monitoring(self):
        """Start background monitoring"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        
        # Start Prometheus HTTP server
        try:
            start_http_server(self.prometheus_port, registry=self.registry)
            logger.info(f"Prometheus metrics server started on port {self.prometheus_port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")
        
        # Start background monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Model monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Model monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                self._check_alerts()
                time.sleep(30)  # Collect metrics every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def record_inference(
        self, 
        inference_time_ms: float,
        predicted_category: str,
        confidence: float,
        confidence_level: str,
        model_version: str,
        is_correct: Optional[bool] = None
    ):
        """Record a model inference"""
        
        with self.lock:
            self.total_requests += 1
            self.inference_times.append(inference_time_ms)
            self.current_model_version = model_version
            self.model_versions.add(model_version)
            
            # Update Prometheus metrics
            self.prom_inference_time.labels(
                model_version=model_version,
                category=predicted_category
            ).observe(inference_time_ms / 1000)  # Convert to seconds
            
            self.prom_predictions_total.labels(
                model_version=model_version,
                confidence_level=confidence_level
            ).inc()
            
            # Record accuracy if feedback provided
            if is_correct is not None:
                self.accuracy_buffer.append(1.0 if is_correct else 0.0)
                current_accuracy = statistics.mean(self.accuracy_buffer)
                self.prom_accuracy_gauge.labels(model_version=model_version).set(current_accuracy)
            
            # Store detailed metrics
            metric = ModelMetric(
                name="inference",
                value=inference_time_ms,
                timestamp=datetime.now(),
                model_version=model_version,
                labels={
                    'category': predicted_category,
                    'confidence_level': confidence_level,
                    'confidence': str(confidence)
                }
            )
            self.metrics_buffer.append(metric)
    
    def record_error(self, error_type: str, model_version: str, details: str = None):
        """Record a model error"""
        
        with self.lock:
            self.error_count += 1
            
            # Update error rate
            error_rate = self.error_count / max(1, self.total_requests)
            self.prom_error_rate.labels(model_version=model_version).set(error_rate)
            
            # Log error
            logger.error(f"ML Model Error [{error_type}]: {details}")
            
            # Store error metric
            metric = ModelMetric(
                name="error",
                value=1.0,
                timestamp=datetime.now(),
                model_version=model_version,
                labels={
                    'error_type': error_type,
                    'details': details or 'none'
                }
            )
            self.metrics_buffer.append(metric)
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        
        try:
            # Memory usage
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            with self.lock:
                # Update Prometheus gauges
                self.prom_memory_usage.labels(
                    model_version=self.current_model_version
                ).set(memory_info.used)
                
                self.prom_cpu_usage.labels(
                    model_version=self.current_model_version
                ).set(cpu_percent)
                
                # Store system metrics
                metrics = [
                    ModelMetric(
                        name="memory_usage_mb",
                        value=memory_mb,
                        timestamp=datetime.now(),
                        model_version=self.current_model_version
                    ),
                    ModelMetric(
                        name="cpu_usage_percent", 
                        value=cpu_percent,
                        timestamp=datetime.now(),
                        model_version=self.current_model_version
                    )
                ]
                
                for metric in metrics:
                    self.metrics_buffer.append(metric)
                    
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def update_cache_metrics(self, hit_rate: float, cache_size: int):
        """Update cache performance metrics"""
        
        with self.lock:
            self.prom_cache_hit_rate.labels(
                model_version=self.current_model_version
            ).set(hit_rate)
            
            metric = ModelMetric(
                name="cache_hit_rate",
                value=hit_rate,
                timestamp=datetime.now(),
                model_version=self.current_model_version,
                labels={'cache_size': str(cache_size)}
            )
            self.metrics_buffer.append(metric)
    
    def _check_alerts(self):
        """Check for alert conditions"""
        
        try:
            with self.lock:
                current_time = datetime.now()
                
                # Check inference time
                if self.inference_times:
                    avg_time = statistics.mean(self.inference_times)
                    p95_time = np.percentile(list(self.inference_times), 95)
                    
                    self._check_threshold_alert(
                        'inference_time_ms',
                        avg_time,
                        f"Average inference time: {avg_time:.2f}ms"
                    )
                
                # Check error rate
                if self.total_requests > 0:
                    error_rate = self.error_count / self.total_requests
                    self._check_threshold_alert(
                        'error_rate',
                        error_rate,
                        f"Error rate: {error_rate:.3f}"
                    )
                
                # Check accuracy
                if self.accuracy_buffer:
                    accuracy = statistics.mean(self.accuracy_buffer)
                    # For accuracy, we alert if it's below threshold (inverted logic)
                    if accuracy < self.alert_thresholds['accuracy']['critical']:
                        self._create_alert(
                            AlertLevel.CRITICAL,
                            'accuracy',
                            accuracy,
                            self.alert_thresholds['accuracy']['critical'],
                            f"Model accuracy critically low: {accuracy:.3f}"
                        )
                    elif accuracy < self.alert_thresholds['accuracy']['warning']:
                        self._create_alert(
                            AlertLevel.WARNING,
                            'accuracy',
                            accuracy,
                            self.alert_thresholds['accuracy']['warning'],
                            f"Model accuracy below warning threshold: {accuracy:.3f}"
                        )
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _check_threshold_alert(self, metric_name: str, value: float, message: str):
        """Check if metric exceeds thresholds"""
        
        thresholds = self.alert_thresholds.get(metric_name, {})
        
        if value >= thresholds.get('critical', float('inf')):
            self._create_alert(
                AlertLevel.CRITICAL,
                metric_name,
                value,
                thresholds['critical'],
                message
            )
        elif value >= thresholds.get('warning', float('inf')):
            self._create_alert(
                AlertLevel.WARNING,
                metric_name,
                value,
                thresholds['warning'],
                message
            )
    
    def _create_alert(
        self, 
        level: AlertLevel, 
        metric_name: str, 
        value: float, 
        threshold: float, 
        message: str
    ):
        """Create and store an alert"""
        
        alert = Alert(
            level=level,
            message=message,
            timestamp=datetime.now(),
            metric_name=metric_name,
            current_value=value,
            threshold=threshold,
            model_version=self.current_model_version
        )
        
        self.alerts_history.append(alert)
        
        # Log alert
        log_func = logger.critical if level == AlertLevel.CRITICAL else logger.warning
        log_func(f"ML Model Alert [{level.value.upper()}]: {message}")
    
    def get_performance_snapshot(self) -> PerformanceSnapshot:
        """Get current performance snapshot"""
        
        with self.lock:
            # Calculate inference time metrics
            if self.inference_times:
                inference_times_list = list(self.inference_times)
                avg_inference_time = statistics.mean(inference_times_list)
                p95_inference_time = np.percentile(inference_times_list, 95)
                p99_inference_time = np.percentile(inference_times_list, 99)
                throughput = len(inference_times_list) / max(1, len(inference_times_list) / 1000)
            else:
                avg_inference_time = p95_inference_time = p99_inference_time = 0.0
                throughput = 0.0
            
            # Calculate accuracy
            accuracy = statistics.mean(self.accuracy_buffer) if self.accuracy_buffer else 0.0
            
            # Calculate error rate
            error_rate = self.error_count / max(1, self.total_requests)
            
            # Get system metrics
            memory_info = psutil.virtual_memory()
            cpu_usage = psutil.cpu_percent()
            
            # Get cache hit rate (from latest metric)
            cache_hit_rate = 0.0
            for metric in reversed(self.metrics_buffer):
                if metric.name == 'cache_hit_rate':
                    cache_hit_rate = metric.value
                    break
            
            return PerformanceSnapshot(
                timestamp=datetime.now(),
                model_version=self.current_model_version,
                avg_inference_time_ms=avg_inference_time,
                p95_inference_time_ms=p95_inference_time,
                p99_inference_time_ms=p99_inference_time,
                throughput_per_second=throughput,
                accuracy=accuracy,
                error_rate=error_rate,
                memory_usage_mb=memory_info.used / (1024 * 1024),
                cpu_usage_percent=cpu_usage,
                cache_hit_rate=cache_hit_rate,
                total_predictions=self.total_requests
            )
    
    def get_metrics_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive metrics for dashboard"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            # Filter recent metrics
            recent_metrics = [
                m for m in self.metrics_buffer 
                if m.timestamp >= cutoff_time
            ]
            
            recent_alerts = [
                a for a in self.alerts_history 
                if a.timestamp >= cutoff_time
            ]
            
            # Performance snapshot
            snapshot = self.get_performance_snapshot()
            
            # Aggregate metrics by type
            metrics_by_type = defaultdict(list)
            for metric in recent_metrics:
                metrics_by_type[metric.name].append(metric.value)
            
            # Alert summary
            alert_counts = {level.value: 0 for level in AlertLevel}
            for alert in recent_alerts:
                alert_counts[alert.level.value] += 1
            
            return {
                'current_snapshot': asdict(snapshot),
                'metrics_summary': {
                    name: {
                        'count': len(values),
                        'avg': statistics.mean(values) if values else 0,
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0
                    }
                    for name, values in metrics_by_type.items()
                },
                'alert_summary': alert_counts,
                'recent_alerts': [asdict(a) for a in list(recent_alerts)[-10:]],
                'model_versions': list(self.model_versions),
                'time_range_hours': hours,
                'prometheus_port': self.prometheus_port
            }
    
    def export_metrics_csv(self, filepath: str, hours: int = 24):
        """Export metrics to CSV file"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            metrics_data = []
            
            for metric in self.metrics_buffer:
                if metric.timestamp >= cutoff_time:
                    row = {
                        'timestamp': metric.timestamp.isoformat(),
                        'name': metric.name,
                        'value': metric.value,
                        'model_version': metric.model_version
                    }
                    
                    if metric.labels:
                        row.update(metric.labels)
                    
                    metrics_data.append(row)
            
            df = pd.DataFrame(metrics_data)
            df.to_csv(filepath, index=False)
            
            logger.info(f"Metrics exported to {filepath}")
    
    def set_alert_threshold(self, metric_name: str, level: str, threshold: float):
        """Update alert threshold"""
        
        if metric_name not in self.alert_thresholds:
            self.alert_thresholds[metric_name] = {}
        
        self.alert_thresholds[metric_name][level] = threshold
        
        logger.info(f"Updated alert threshold: {metric_name}.{level} = {threshold}")

# Global monitor instance
model_monitor = ModelMonitor()