"""
Database monitoring and performance tracking service
"""
import time
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db_session
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
db_queries_total = Counter('db_queries_total', 'Total database queries', ['operation', 'table'])
db_query_duration = Histogram('db_query_duration_seconds', 'Database query duration', ['operation', 'table'])
db_connections_active = Gauge('db_connections_active', 'Active database connections')
db_slow_queries_total = Counter('db_slow_queries_total', 'Total slow database queries', ['query_type'])

class DatabaseMonitoringService:
    """Service for monitoring database performance and health"""
    
    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
    
    def track_query_performance(self, operation: str, table: str, duration: float):
        """Track query performance metrics"""
        db_queries_total.labels(operation=operation, table=table).inc()
        db_query_duration.labels(operation=operation, table=table).observe(duration)
        
        if duration > self.slow_query_threshold:
            db_slow_queries_total.labels(query_type=operation).inc()
            logger.warning(f"Slow query detected: {operation} on {table} took {duration:.2f}s")
    
    def get_database_stats(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {}
        
        try:
            # Connection statistics
            result = db.execute(text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """))
            conn_stats = result.fetchone()
            stats['connections'] = {
                'total': conn_stats.total_connections,
                'active': conn_stats.active_connections,
                'idle': conn_stats.idle_connections
            }
            
            # Database size
            result = db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
            """))
            stats['database_size'] = result.scalar()
            
            # Table statistics
            result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_stat_user_tables 
                ORDER BY n_live_tup DESC
                LIMIT 10
            """))
            stats['top_tables'] = [dict(row) for row in result.fetchall()]
            
            # Index usage
            result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes 
                WHERE idx_scan > 0
                ORDER BY idx_scan DESC
                LIMIT 10
            """))
            stats['index_usage'] = [dict(row) for row in result.fetchall()]
            
            # Slow queries (if pg_stat_statements is available)
            try:
                result = db.execute(text("""
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE mean_time > 100
                    ORDER BY mean_time DESC
                    LIMIT 5
                """))
                stats['slow_queries'] = [dict(row) for row in result.fetchall()]
            except Exception:
                stats['slow_queries'] = []  # pg_stat_statements not available
            
        except Exception as e:
            logger.error(f"Error collecting database stats: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def check_database_health(self, db: Session) -> Dict[str, Any]:
        """Perform database health checks"""
        health = {
            'status': 'healthy',
            'checks': {},
            'recommendations': []
        }
        
        try:
            # Check connection pool
            stats = self.get_database_stats(db)
            conn_stats = stats.get('connections', {})
            
            if conn_stats.get('active', 0) > 50:  # Configurable threshold
                health['checks']['high_connection_count'] = {
                    'status': 'warning',
                    'value': conn_stats.get('active'),
                    'message': 'High number of active connections'
                }
                health['recommendations'].append('Consider connection pooling optimization')
            
            # Check for dead tuples (need for VACUUM)
            dead_tuple_threshold = 1000
            for table in stats.get('top_tables', []):
                dead_tuples = table.get('dead_tuples', 0)
                if dead_tuples > dead_tuple_threshold:
                    health['checks'][f'dead_tuples_{table["tablename"]}'] = {
                        'status': 'warning',
                        'value': dead_tuples,
                        'message': f'High dead tuple count in {table["tablename"]}'
                    }
                    health['recommendations'].append(f'Run VACUUM on {table["tablename"]}')
            
            # Check for unused indexes
            for index in stats.get('index_usage', []):
                if index.get('index_scans', 0) == 0:
                    health['checks'][f'unused_index_{index["indexname"]}'] = {
                        'status': 'info',
                        'message': f'Index {index["indexname"]} is not being used'
                    }
                    health['recommendations'].append(f'Consider dropping unused index {index["indexname"]}')
            
            # Overall health assessment
            warning_count = sum(1 for check in health['checks'].values() if check.get('status') == 'warning')
            if warning_count > 3:
                health['status'] = 'degraded'
            elif warning_count > 0:
                health['status'] = 'warning'
            
        except Exception as e:
            logger.error(f"Error during database health check: {e}")
            health['status'] = 'error'
            health['error'] = str(e)
        
        return health
    
    def optimize_query_performance(self, db: Session) -> List[str]:
        """Analyze and suggest query optimizations"""
        suggestions = []
        
        try:
            # Check for missing indexes on foreign keys
            result = db.execute(text("""
                SELECT 
                    t.table_name,
                    c.column_name,
                    c.constraint_name
                FROM information_schema.table_constraints t
                JOIN information_schema.constraint_column_usage c
                ON t.constraint_name = c.constraint_name
                WHERE t.constraint_type = 'FOREIGN KEY'
                AND NOT EXISTS (
                    SELECT 1 FROM pg_indexes i 
                    WHERE i.tablename = t.table_name 
                    AND i.indexdef LIKE '%' || c.column_name || '%'
                )
            """))
            
            missing_fk_indexes = result.fetchall()
            for row in missing_fk_indexes:
                suggestions.append(f"Consider adding index on {row.table_name}.{row.column_name} (foreign key)")
            
            # Check for tables without primary keys
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                AND NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints tc
                    WHERE tc.table_name = t.table_name
                    AND tc.constraint_type = 'PRIMARY KEY'
                )
            """))
            
            tables_without_pk = result.fetchall()
            for row in tables_without_pk:
                suggestions.append(f"Table {row.table_name} lacks a primary key")
            
        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            suggestions.append(f"Error during analysis: {str(e)}")
        
        return suggestions

# Create global monitoring service
monitoring_service = DatabaseMonitoringService()