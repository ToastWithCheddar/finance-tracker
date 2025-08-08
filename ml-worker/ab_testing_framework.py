"""
A/B Testing Framework for ML Models
Statistical testing, traffic splitting, and performance comparison
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import statistics
from collections import defaultdict

import numpy as np
from scipy import stats
import pandas as pd

logger = logging.getLogger(__name__)

class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TrafficSplitStrategy(Enum):
    RANDOM = "random"
    USER_ID_HASH = "user_id_hash"
    GEOGRAPHIC = "geographic"
    TIME_BASED = "time_based"

@dataclass
class ModelVariant:
    name: str
    model_path: str
    model_version: str
    weight: float  # Traffic allocation percentage (0.0 to 1.0)
    description: str = ""
    config: Dict[str, Any] = None

@dataclass
class ExperimentConfig:
    experiment_id: str
    name: str
    description: str
    variants: List[ModelVariant]
    traffic_split_strategy: TrafficSplitStrategy
    start_time: datetime
    end_time: Optional[datetime]
    success_metrics: List[str]  # e.g., ['accuracy', 'inference_time', 'user_satisfaction']
    minimum_sample_size: int
    statistical_power: float = 0.8
    significance_level: float = 0.05
    guard_rails: Dict[str, float] = None  # Safety thresholds

@dataclass
class ExperimentResult:
    timestamp: datetime
    experiment_id: str
    variant_name: str
    user_id: Optional[str]
    prediction: str
    confidence: float
    inference_time_ms: float
    is_correct: Optional[bool]
    user_feedback: Optional[Dict[str, Any]]
    metadata: Dict[str, Any] = None

@dataclass
class StatisticalTest:
    test_name: str
    variant_a: str
    variant_b: str
    metric: str
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    sample_size_a: int
    sample_size_b: int
    power: float

class ABTestingFramework:
    """A/B Testing framework for ML model experiments"""
    
    def __init__(self, results_storage_path: str = "ab_test_results"):
        self.results_storage_path = results_storage_path
        self.experiments: Dict[str, ExperimentConfig] = {}
        self.results: Dict[str, List[ExperimentResult]] = defaultdict(list)
        self.experiment_status: Dict[str, ExperimentStatus] = {}
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Statistical testing configuration
        self.min_sample_size_for_test = 30
        self.confidence_levels = [0.90, 0.95, 0.99]
        
        os.makedirs(results_storage_path, exist_ok=True)
        
    def create_experiment(self, config: ExperimentConfig) -> str:
        """Create a new A/B testing experiment"""
        
        # Validate configuration
        self._validate_experiment_config(config)
        
        with self.lock:
            self.experiments[config.experiment_id] = config
            self.experiment_status[config.experiment_id] = ExperimentStatus.DRAFT
            self.results[config.experiment_id] = []
            
            # Save experiment config
            self._save_experiment_config(config)
            
            logger.info(f"Created experiment: {config.experiment_id}")
            return config.experiment_id
    
    def _validate_experiment_config(self, config: ExperimentConfig):
        """Validate experiment configuration"""
        
        # Check traffic allocation
        total_weight = sum(v.weight for v in config.variants)
        if not (0.99 <= total_weight <= 1.01):  # Allow small floating point errors
            raise ValueError(f"Variant weights must sum to 1.0, got {total_weight}")
        
        # Check minimum requirements
        if len(config.variants) < 2:
            raise ValueError("Experiment must have at least 2 variants")
        
        # Check variant names are unique
        variant_names = [v.name for v in config.variants]
        if len(variant_names) != len(set(variant_names)):
            raise ValueError("Variant names must be unique")
        
        # Check time validity
        if config.end_time and config.end_time <= config.start_time:
            raise ValueError("End time must be after start time")
    
    def start_experiment(self, experiment_id: str):
        """Start an experiment"""
        
        with self.lock:
            if experiment_id not in self.experiments:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            config = self.experiments[experiment_id]
            
            # Check if it's time to start
            if datetime.now() < config.start_time:
                raise ValueError(f"Experiment start time is in the future: {config.start_time}")
            
            self.experiment_status[experiment_id] = ExperimentStatus.RUNNING
            
            logger.info(f"Started experiment: {experiment_id}")
    
    def stop_experiment(self, experiment_id: str, reason: str = "manual_stop"):
        """Stop an experiment"""
        
        with self.lock:
            if experiment_id not in self.experiments:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            self.experiment_status[experiment_id] = ExperimentStatus.COMPLETED
            
            # Generate final report
            report = self.generate_experiment_report(experiment_id)
            self._save_experiment_report(experiment_id, report)
            
            logger.info(f"Stopped experiment: {experiment_id} ({reason})")
    
    def assign_variant(
        self, 
        experiment_id: str, 
        user_id: str = None,
        context: Dict[str, Any] = None
    ) -> Optional[ModelVariant]:
        """Assign a user to a variant based on the traffic splitting strategy"""
        
        with self.lock:
            if experiment_id not in self.experiments:
                return None
            
            if self.experiment_status[experiment_id] != ExperimentStatus.RUNNING:
                return None
            
            config = self.experiments[experiment_id]
            
            # Check if experiment has ended
            if config.end_time and datetime.now() > config.end_time:
                self.stop_experiment(experiment_id, "time_expired")
                return None
            
            # Apply guard rails
            if self._check_guard_rails(experiment_id):
                logger.warning(f"Guard rails triggered for experiment {experiment_id}")
                self.experiment_status[experiment_id] = ExperimentStatus.PAUSED
                return None
            
            # Assign variant based on strategy
            variant = self._assign_variant_by_strategy(config, user_id, context)
            
            return variant
    
    def _assign_variant_by_strategy(
        self, 
        config: ExperimentConfig, 
        user_id: str,
        context: Dict[str, Any]
    ) -> ModelVariant:
        """Assign variant based on traffic split strategy"""
        
        if config.traffic_split_strategy == TrafficSplitStrategy.RANDOM:
            return self._random_assignment(config.variants)
        
        elif config.traffic_split_strategy == TrafficSplitStrategy.USER_ID_HASH:
            return self._hash_based_assignment(config.variants, user_id or "anonymous")
        
        elif config.traffic_split_strategy == TrafficSplitStrategy.TIME_BASED:
            return self._time_based_assignment(config.variants)
        
        else:
            # Default to random
            return self._random_assignment(config.variants)
    
    def _random_assignment(self, variants: List[ModelVariant]) -> ModelVariant:
        """Random traffic assignment"""
        rand_val = np.random.random()
        cumulative_weight = 0.0
        
        for variant in variants:
            cumulative_weight += variant.weight
            if rand_val <= cumulative_weight:
                return variant
        
        return variants[-1]  # Fallback
    
    def _hash_based_assignment(self, variants: List[ModelVariant], user_id: str) -> ModelVariant:
        """Consistent hash-based assignment"""
        # Create deterministic hash
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        normalized_hash = (hash_val % 10000) / 10000.0
        
        cumulative_weight = 0.0
        for variant in variants:
            cumulative_weight += variant.weight
            if normalized_hash <= cumulative_weight:
                return variant
        
        return variants[-1]  # Fallback
    
    def _time_based_assignment(self, variants: List[ModelVariant]) -> ModelVariant:
        """Time-based assignment (cyclical)"""
        # Use current minute to cycle through variants
        minute = datetime.now().minute
        total_minutes = 60
        
        cumulative_weight = 0.0
        normalized_time = (minute % total_minutes) / total_minutes
        
        for variant in variants:
            cumulative_weight += variant.weight
            if normalized_time <= cumulative_weight:
                return variant
        
        return variants[-1]  # Fallback
    
    def record_result(
        self, 
        experiment_id: str,
        variant_name: str,
        user_id: Optional[str],
        prediction: str,
        confidence: float,
        inference_time_ms: float,
        is_correct: Optional[bool] = None,
        user_feedback: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record an experiment result"""
        
        result = ExperimentResult(
            timestamp=datetime.now(),
            experiment_id=experiment_id,
            variant_name=variant_name,
            user_id=user_id,
            prediction=prediction,
            confidence=confidence,
            inference_time_ms=inference_time_ms,
            is_correct=is_correct,
            user_feedback=user_feedback,
            metadata=metadata or {}
        )
        
        with self.lock:
            self.results[experiment_id].append(result)
            
            # Periodically save results
            if len(self.results[experiment_id]) % 100 == 0:
                self._save_experiment_results(experiment_id)
    
    def _check_guard_rails(self, experiment_id: str) -> bool:
        """Check if experiment should be stopped due to guard rails"""
        
        config = self.experiments[experiment_id]
        if not config.guard_rails:
            return False
        
        results = self.results[experiment_id]
        if len(results) < 50:  # Need minimum sample size
            return False
        
        # Check each variant against guard rails
        for variant in config.variants:
            variant_results = [r for r in results if r.variant_name == variant.name]
            
            if len(variant_results) < 20:
                continue
            
            # Check accuracy guard rail
            if 'min_accuracy' in config.guard_rails:
                correct_predictions = [r for r in variant_results if r.is_correct is True]
                accuracy = len(correct_predictions) / len([r for r in variant_results if r.is_correct is not None])
                
                if accuracy < config.guard_rails['min_accuracy']:
                    logger.warning(f"Guard rail triggered: {variant.name} accuracy {accuracy:.3f} below {config.guard_rails['min_accuracy']}")
                    return True
            
            # Check inference time guard rail
            if 'max_inference_time_ms' in config.guard_rails:
                avg_time = statistics.mean([r.inference_time_ms for r in variant_results])
                
                if avg_time > config.guard_rails['max_inference_time_ms']:
                    logger.warning(f"Guard rail triggered: {variant.name} avg inference time {avg_time:.1f}ms above {config.guard_rails['max_inference_time_ms']}")
                    return True
        
        return False
    
    def run_statistical_analysis(self, experiment_id: str) -> List[StatisticalTest]:
        """Run statistical analysis comparing variants"""
        
        with self.lock:
            results = self.results[experiment_id]
            config = self.experiments[experiment_id]
            
            if len(results) < self.min_sample_size_for_test:
                logger.warning(f"Insufficient sample size for statistical testing: {len(results)}")
                return []
            
            tests = []
            variants = config.variants
            
            # Compare each pair of variants
            for i in range(len(variants)):
                for j in range(i + 1, len(variants)):
                    variant_a = variants[i]
                    variant_b = variants[j]
                    
                    # Run tests for each success metric
                    for metric in config.success_metrics:
                        test = self._run_statistical_test(
                            results, variant_a.name, variant_b.name, metric
                        )
                        if test:
                            tests.append(test)
            
            return tests
    
    def _run_statistical_test(
        self, 
        results: List[ExperimentResult],
        variant_a: str,
        variant_b: str,
        metric: str
    ) -> Optional[StatisticalTest]:
        """Run statistical test between two variants for a metric"""
        
        # Filter results by variant
        results_a = [r for r in results if r.variant_name == variant_a]
        results_b = [r for r in results if r.variant_name == variant_b]
        
        if len(results_a) < self.min_sample_size_for_test or len(results_b) < self.min_sample_size_for_test:
            return None
        
        # Extract metric values
        if metric == 'accuracy':
            # Binary accuracy test
            values_a = [1 if r.is_correct else 0 for r in results_a if r.is_correct is not None]
            values_b = [1 if r.is_correct else 0 for r in results_b if r.is_correct is not None]
            
            if not values_a or not values_b:
                return None
            
            # Two-proportion z-test
            count_a, count_b = sum(values_a), sum(values_b)
            n_a, n_b = len(values_a), len(values_b)
            
            # Calculate proportions
            p_a, p_b = count_a / n_a, count_b / n_b
            p_pooled = (count_a + count_b) / (n_a + n_b)
            
            # Calculate test statistic
            se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n_a + 1/n_b))
            z_stat = (p_a - p_b) / se if se > 0 else 0
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
            
            # Effect size (Cohen's h)
            effect_size = 2 * (np.arcsin(np.sqrt(p_a)) - np.arcsin(np.sqrt(p_b)))
            
            # Confidence interval for difference in proportions
            se_diff = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
            margin_error = stats.norm.ppf(0.975) * se_diff
            ci = ((p_a - p_b) - margin_error, (p_a - p_b) + margin_error)
            
        elif metric == 'inference_time':
            # Continuous metric test
            values_a = [r.inference_time_ms for r in results_a]
            values_b = [r.inference_time_ms for r in results_b]
            
            # Two-sample t-test
            t_stat, p_value = stats.ttest_ind(values_a, values_b)
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt(((len(values_a) - 1) * np.var(values_a, ddof=1) + 
                                 (len(values_b) - 1) * np.var(values_b, ddof=1)) / 
                                (len(values_a) + len(values_b) - 2))
            effect_size = (np.mean(values_a) - np.mean(values_b)) / pooled_std if pooled_std > 0 else 0
            
            # Confidence interval for difference in means
            se_diff = pooled_std * np.sqrt(1/len(values_a) + 1/len(values_b))
            df = len(values_a) + len(values_b) - 2
            margin_error = stats.t.ppf(0.975, df) * se_diff
            mean_diff = np.mean(values_a) - np.mean(values_b)
            ci = (mean_diff - margin_error, mean_diff + margin_error)
            
        elif metric == 'confidence':
            # Continuous metric test
            values_a = [r.confidence for r in results_a]
            values_b = [r.confidence for r in results_b]
            
            t_stat, p_value = stats.ttest_ind(values_a, values_b)
            
            pooled_std = np.sqrt(((len(values_a) - 1) * np.var(values_a, ddof=1) + 
                                 (len(values_b) - 1) * np.var(values_b, ddof=1)) / 
                                (len(values_a) + len(values_b) - 2))
            effect_size = (np.mean(values_a) - np.mean(values_b)) / pooled_std if pooled_std > 0 else 0
            
            se_diff = pooled_std * np.sqrt(1/len(values_a) + 1/len(values_b))
            df = len(values_a) + len(values_b) - 2
            margin_error = stats.t.ppf(0.975, df) * se_diff
            mean_diff = np.mean(values_a) - np.mean(values_b)
            ci = (mean_diff - margin_error, mean_diff + margin_error)
        
        else:
            return None
        
        # Calculate statistical power (simplified)
        power = self._calculate_power(len(results_a), len(results_b), effect_size)
        
        return StatisticalTest(
            test_name=f"{variant_a}_vs_{variant_b}_{metric}",
            variant_a=variant_a,
            variant_b=variant_b,
            metric=metric,
            p_value=p_value,
            effect_size=effect_size,
            confidence_interval=ci,
            is_significant=p_value < 0.05,
            sample_size_a=len(results_a),
            sample_size_b=len(results_b),
            power=power
        )
    
    def _calculate_power(self, n_a: int, n_b: int, effect_size: float) -> float:
        """Calculate statistical power (simplified approximation)"""
        try:
            from statsmodels.stats.power import ttest_power
            power = ttest_power(effect_size, n_a, alpha=0.05, alternative='two-sided')
            return min(power, 1.0)
        except ImportError:
            # Simplified approximation if statsmodels not available
            effective_n = (n_a * n_b) / (n_a + n_b)
            z_beta = abs(effect_size) * np.sqrt(effective_n / 2) - stats.norm.ppf(0.975)
            return 1 - stats.norm.cdf(z_beta)
    
    def generate_experiment_report(self, experiment_id: str) -> Dict[str, Any]:
        """Generate comprehensive experiment report"""
        
        with self.lock:
            config = self.experiments[experiment_id]
            results = self.results[experiment_id]
            status = self.experiment_status[experiment_id]
            
            if not results:
                return {
                    'experiment_id': experiment_id,
                    'status': status.value,
                    'error': 'No results available'
                }
            
            # Run statistical analysis
            statistical_tests = self.run_statistical_analysis(experiment_id)
            
            # Calculate summary statistics per variant
            variant_stats = {}
            for variant in config.variants:
                variant_results = [r for r in results if r.variant_name == variant.name]
                
                if variant_results:
                    # Accuracy
                    accuracy_results = [r for r in variant_results if r.is_correct is not None]
                    accuracy = (
                        len([r for r in accuracy_results if r.is_correct]) / len(accuracy_results)
                        if accuracy_results else 0
                    )
                    
                    # Performance metrics
                    inference_times = [r.inference_time_ms for r in variant_results]
                    confidences = [r.confidence for r in variant_results]
                    
                    variant_stats[variant.name] = {
                        'sample_size': len(variant_results),
                        'accuracy': accuracy,
                        'accuracy_samples': len(accuracy_results),
                        'avg_inference_time_ms': statistics.mean(inference_times),
                        'p95_inference_time_ms': np.percentile(inference_times, 95),
                        'avg_confidence': statistics.mean(confidences),
                        'confidence_std': statistics.stdev(confidences) if len(confidences) > 1 else 0
                    }
                else:
                    variant_stats[variant.name] = {
                        'sample_size': 0,
                        'accuracy': 0,
                        'accuracy_samples': 0,
                        'avg_inference_time_ms': 0,
                        'p95_inference_time_ms': 0,
                        'avg_confidence': 0,
                        'confidence_std': 0
                    }
            
            # Find winning variant (highest accuracy)
            winning_variant = max(
                variant_stats.keys(), 
                key=lambda v: variant_stats[v]['accuracy']
            )
            
            # Calculate experiment duration
            if results:
                start_time = min(r.timestamp for r in results)
                end_time = max(r.timestamp for r in results)
                duration_hours = (end_time - start_time).total_seconds() / 3600
            else:
                duration_hours = 0
            
            return {
                'experiment_id': experiment_id,
                'experiment_name': config.name,
                'status': status.value,
                'start_time': config.start_time.isoformat(),
                'end_time': config.end_time.isoformat() if config.end_time else None,
                'duration_hours': duration_hours,
                'total_samples': len(results),
                'variants': [asdict(v) for v in config.variants],
                'variant_statistics': variant_stats,
                'winning_variant': winning_variant,
                'statistical_tests': [asdict(test) for test in statistical_tests],
                'significant_results': [
                    asdict(test) for test in statistical_tests if test.is_significant
                ],
                'success_metrics': config.success_metrics,
                'recommendations': self._generate_recommendations(variant_stats, statistical_tests),
                'generated_at': datetime.now().isoformat()
            }
    
    def _generate_recommendations(
        self, 
        variant_stats: Dict[str, Any], 
        tests: List[StatisticalTest]
    ) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Check for clear winner
        significant_accuracy_tests = [
            t for t in tests 
            if t.metric == 'accuracy' and t.is_significant and abs(t.effect_size) > 0.2
        ]
        
        if significant_accuracy_tests:
            best_test = max(significant_accuracy_tests, key=lambda t: abs(t.effect_size))
            recommendations.append(
                f"Strong evidence for {best_test.variant_a} over {best_test.variant_b} "
                f"in accuracy (p={best_test.p_value:.4f}, effect size={best_test.effect_size:.3f})"
            )
        
        # Check for performance issues
        performance_tests = [t for t in tests if t.metric == 'inference_time' and t.is_significant]
        if performance_tests:
            for test in performance_tests:
                if test.effect_size > 0.5:  # Large effect size
                    recommendations.append(
                        f"Significant performance difference: {test.variant_a} vs {test.variant_b} "
                        f"in inference time (p={test.p_value:.4f})"
                    )
        
        # Sample size recommendations
        low_power_tests = [t for t in tests if t.power < 0.8]
        if low_power_tests:
            recommendations.append(
                "Some comparisons have low statistical power (<80%). Consider collecting more data."
            )
        
        # Overall recommendation
        if not significant_accuracy_tests and not performance_tests:
            recommendations.append(
                "No significant differences detected. Consider extending the experiment or "
                "collecting more samples for conclusive results."
            )
        
        return recommendations
    
    def _save_experiment_config(self, config: ExperimentConfig):
        """Save experiment configuration to file"""
        config_path = os.path.join(self.results_storage_path, f"{config.experiment_id}_config.json")
        
        config_dict = asdict(config)
        config_dict['start_time'] = config.start_time.isoformat()
        config_dict['end_time'] = config.end_time.isoformat() if config.end_time else None
        config_dict['traffic_split_strategy'] = config.traffic_split_strategy.value
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def _save_experiment_results(self, experiment_id: str):
        """Save experiment results to file"""
        results_path = os.path.join(self.results_storage_path, f"{experiment_id}_results.jsonl")
        
        with open(results_path, 'w') as f:
            for result in self.results[experiment_id]:
                result_dict = asdict(result)
                result_dict['timestamp'] = result.timestamp.isoformat()
                f.write(json.dumps(result_dict) + '\n')
    
    def _save_experiment_report(self, experiment_id: str, report: Dict[str, Any]):
        """Save experiment report to file"""
        report_path = os.path.join(self.results_storage_path, f"{experiment_id}_report.json")
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

# Global A/B testing framework instance
ab_framework = ABTestingFramework()