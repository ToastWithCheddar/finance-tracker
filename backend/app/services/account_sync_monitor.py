"""
Account Sync Monitor and Status Service
Real-time monitoring and status tracking for account synchronization
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum
import asyncio

from app.models.account import Account
from app.models.user import User
from app.services.enhanced_plaid_service import enhanced_plaid_service
from app.services.transaction_sync_service import transaction_sync_service
from app.websocket.manager import websocket_manager
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)

class SyncHealth(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"

class SyncFrequency(Enum):
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MANUAL = "manual"

@dataclass
class AccountSyncStatus:
    """Comprehensive sync status for an account"""
    account_id: str
    account_name: str
    account_type: str
    is_plaid_connected: bool
    sync_health: SyncHealth
    sync_frequency: SyncFrequency
    last_sync: Optional[datetime]
    last_successful_sync: Optional[datetime]
    next_scheduled_sync: Optional[datetime]
    sync_errors: List[str]
    balance_sync_status: str
    transaction_sync_status: str
    connection_quality: int  # 0-100 score
    sync_performance: Dict[str, Any]
    recommendations: List[str]

class AccountSyncMonitor:
    """Monitor and track account synchronization status"""
    
    def __init__(self):
        self.plaid_service = enhanced_plaid_service
        self.sync_service = transaction_sync_service
        
        # Health check thresholds
        self.health_thresholds = {
            'critical_hours': 168,  # 7 days
            'warning_hours': 48,    # 2 days
            'healthy_hours': 24     # 1 day
        }
        
        # Performance tracking
        self.sync_metrics = {}
    
    async def get_account_sync_status(self, account_id: str, db: Session) -> AccountSyncStatus:
        """Get comprehensive sync status for a single account"""
        
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise Exception(f"Account {account_id} not found")
        
        # Calculate sync health
        sync_health = self._calculate_sync_health(account)
        
        # Determine sync frequency
        sync_frequency = self._determine_sync_frequency(account)
        
        # Get connection quality score
        connection_quality = await self._calculate_connection_quality(account, db)
        
        # Get sync performance metrics
        sync_performance = await self._get_sync_performance(account, db)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(account, sync_health, connection_quality)
        
        # Calculate next sync time
        next_scheduled_sync = self._calculate_next_sync(account, sync_frequency)
        
        return AccountSyncStatus(
            account_id=str(account.id),
            account_name=account.name,
            account_type=account.account_type,
            is_plaid_connected=account.is_plaid_connected,
            sync_health=sync_health,
            sync_frequency=sync_frequency,
            last_sync=account.last_sync_at,
            last_successful_sync=self._get_last_successful_sync(account),
            next_scheduled_sync=next_scheduled_sync,
            sync_errors=self._get_recent_sync_errors(account),
            balance_sync_status=account.sync_status,
            transaction_sync_status=self._get_transaction_sync_status(account),
            connection_quality=connection_quality,
            sync_performance=sync_performance,
            recommendations=recommendations
        )
    
    async def get_user_sync_overview(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Get sync overview for all user's accounts"""
        
        accounts = db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        if not accounts:
            return {
                'total_accounts': 0,
                'connected_accounts': 0,
                'healthy_accounts': 0,
                'accounts_needing_attention': 0,
                'overall_health_score': 100,
                'accounts': []
            }
        
        # Get status for each account
        account_statuses = []
        for account in accounts:
            try:
                status = await self.get_account_sync_status(str(account.id), db)
                account_statuses.append(status)
            except Exception as e:
                logger.error(f"Failed to get status for account {account.id}: {e}")
        
        # Calculate overview metrics
        total_accounts = len(accounts)
        connected_accounts = sum(1 for status in account_statuses if status.is_plaid_connected)
        healthy_accounts = sum(1 for status in account_statuses 
                             if status.sync_health == SyncHealth.HEALTHY)
        accounts_needing_attention = sum(1 for status in account_statuses 
                                       if status.sync_health in [SyncHealth.WARNING, SyncHealth.CRITICAL])
        
        # Calculate overall health score
        if account_statuses:
            avg_quality = sum(status.connection_quality for status in account_statuses) / len(account_statuses)
        else:
            avg_quality = 0
        
        return {
            'total_accounts': total_accounts,
            'connected_accounts': connected_accounts,
            'healthy_accounts': healthy_accounts,
            'accounts_needing_attention': accounts_needing_attention,
            'overall_health_score': int(avg_quality),
            'sync_status_summary': {
                'healthy': sum(1 for s in account_statuses if s.sync_health == SyncHealth.HEALTHY),
                'warning': sum(1 for s in account_statuses if s.sync_health == SyncHealth.WARNING),
                'critical': sum(1 for s in account_statuses if s.sync_health == SyncHealth.CRITICAL),
                'disconnected': sum(1 for s in account_statuses if s.sync_health == SyncHealth.DISCONNECTED)
            },
            'accounts': [
                {
                    'account_id': status.account_id,
                    'name': status.account_name,
                    'type': status.account_type,
                    'sync_health': status.sync_health.value,
                    'connection_quality': status.connection_quality,
                    'last_sync': status.last_sync.isoformat() if status.last_sync else None,
                    'is_connected': status.is_plaid_connected,
                    'needs_attention': status.sync_health in [SyncHealth.WARNING, SyncHealth.CRITICAL]
                }
                for status in account_statuses
            ]
        }
    
    def _calculate_sync_health(self, account: Account) -> SyncHealth:
        """Calculate sync health based on account status"""
        
        if not account.is_plaid_connected:
            return SyncHealth.DISCONNECTED
        
        if account.sync_status == 'error':
            return SyncHealth.CRITICAL
        
        if not account.last_sync_at:
            return SyncHealth.CRITICAL
        
        # Calculate hours since last sync
        hours_since_sync = (datetime.now(timezone.utc) - account.last_sync_at).total_seconds() / 3600
        
        if hours_since_sync > self.health_thresholds['critical_hours']:
            return SyncHealth.CRITICAL
        elif hours_since_sync > self.health_thresholds['warning_hours']:
            return SyncHealth.WARNING
        elif hours_since_sync <= self.health_thresholds['healthy_hours']:
            return SyncHealth.HEALTHY
        else:
            return SyncHealth.WARNING
    
    def _determine_sync_frequency(self, account: Account) -> SyncFrequency:
        """Determine the sync frequency for an account"""
        
        if not account.is_plaid_connected:
            return SyncFrequency.MANUAL
        
        # Use the account's configured frequency if available
        if hasattr(account, 'sync_frequency') and account.sync_frequency:
            try:
                return SyncFrequency(account.sync_frequency)
            except ValueError:
                pass
        
        # Default based on account type
        if account.account_type in ['checking', 'savings']:
            return SyncFrequency.DAILY
        elif account.account_type == 'credit_card':
            return SyncFrequency.DAILY
        elif account.account_type in ['investment', 'retirement']:
            return SyncFrequency.WEEKLY
        else:
            return SyncFrequency.DAILY
    
    async def _calculate_connection_quality(self, account: Account, db: Session) -> int:
        """Calculate connection quality score (0-100)"""
        
        if not account.is_plaid_connected:
            return 0
        
        score = 100
        
        # Subtract points for sync issues
        if account.sync_status == 'error':
            score -= 40
        elif account.sync_status == 'syncing':
            score -= 10  # Minor penalty for ongoing sync
        
        # Subtract points for old syncs
        if account.last_sync_at:
            hours_since_sync = (datetime.now(timezone.utc) - account.last_sync_at).total_seconds() / 3600
            if hours_since_sync > 168:  # 7 days
                score -= 50
            elif hours_since_sync > 48:  # 2 days
                score -= 25
            elif hours_since_sync > 24:  # 1 day
                score -= 10
        else:
            score -= 60  # Never synced
        
        # Subtract points for recent errors
        if account.last_sync_error:
            score -= 20
        
        # Add points for successful sync history
        metadata = account.account_metadata or {}
        sync_history = metadata.get('sync_history', [])
        if sync_history:
            recent_successes = sum(1 for s in sync_history[-5:] if s.get('status') == 'success')
            score += (recent_successes * 2)  # Bonus for recent successful syncs
        
        return max(0, min(100, score))
    
    async def _get_sync_performance(self, account: Account, db: Session) -> Dict[str, Any]:
        """Get sync performance metrics for an account"""
        
        metadata = account.account_metadata or {}
        sync_history = metadata.get('sync_history', [])
        
        if not sync_history:
            return {
                'avg_sync_time': 0,
                'success_rate': 0,
                'last_sync_duration': 0,
                'sync_frequency_compliance': 0
            }
        
        # Calculate metrics from sync history
        recent_history = sync_history[-10:]  # Last 10 syncs
        successful_syncs = [s for s in recent_history if s.get('status') == 'success']
        
        success_rate = len(successful_syncs) / len(recent_history) * 100 if recent_history else 0
        
        # Sync time performance (if available)
        sync_times = [s.get('duration', 0) for s in recent_history if s.get('duration')]
        avg_sync_time = sum(sync_times) / len(sync_times) if sync_times else 0
        
        return {
            'avg_sync_time': avg_sync_time,
            'success_rate': success_rate,
            'last_sync_duration': recent_history[-1].get('duration', 0) if recent_history else 0,
            'total_syncs': len(sync_history),
            'recent_success_count': len(successful_syncs),
            'sync_frequency_compliance': self._calculate_frequency_compliance(account)
        }
    
    def _calculate_frequency_compliance(self, account: Account) -> float:
        """Calculate how well the account complies with its sync frequency"""
        
        if not account.last_sync_at:
            return 0.0
        
        expected_frequency = self._determine_sync_frequency(account)
        hours_since_sync = (datetime.now(timezone.utc) - account.last_sync_at).total_seconds() / 3600
        
        expected_intervals = {
            SyncFrequency.HOURLY: 1,
            SyncFrequency.DAILY: 24,
            SyncFrequency.WEEKLY: 168,
            SyncFrequency.MONTHLY: 720,
            SyncFrequency.MANUAL: float('inf')
        }
        
        expected_hours = expected_intervals.get(expected_frequency, 24)
        
        if expected_hours == float('inf'):
            return 100.0  # Manual accounts always compliant
        
        compliance = max(0, min(100, 100 - (hours_since_sync - expected_hours) / expected_hours * 100))
        return compliance
    
    def _get_last_successful_sync(self, account: Account) -> Optional[datetime]:
        """Get the timestamp of the last successful sync"""
        
        metadata = account.account_metadata or {}
        sync_history = metadata.get('sync_history', [])
        
        for sync_record in reversed(sync_history):
            if sync_record.get('status') == 'success':
                timestamp_str = sync_record.get('timestamp')
                if timestamp_str:
                    try:
                        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except:
                        pass
        
        return None
    
    def _get_recent_sync_errors(self, account: Account) -> List[str]:
        """Get recent sync errors for an account"""
        
        errors = []
        
        if account.last_sync_error:
            errors.append(account.last_sync_error)
        
        # Get errors from sync history
        metadata = account.account_metadata or {}
        sync_history = metadata.get('sync_history', [])
        
        for sync_record in reversed(sync_history[-5:]):  # Last 5 records
            if sync_record.get('status') == 'error' and sync_record.get('error'):
                errors.append(sync_record['error'])
        
        return errors[:3]  # Return max 3 recent errors
    
    def _get_transaction_sync_status(self, account: Account) -> str:
        """Get transaction synchronization status"""
        
        metadata = account.account_metadata or {}
        last_transaction_sync = metadata.get('last_transaction_sync')
        
        if not last_transaction_sync:
            return 'never'
        
        try:
            last_sync_dt = datetime.fromisoformat(last_transaction_sync.replace('Z', '+00:00'))
            hours_since = (datetime.now(timezone.utc) - last_sync_dt).total_seconds() / 3600
            
            if hours_since < 24:
                return 'recent'
            elif hours_since < 168:  # 1 week
                return 'stale'
            else:
                return 'very_stale'
        except:
            return 'unknown'
    
    def _generate_recommendations(
        self, 
        account: Account, 
        sync_health: SyncHealth, 
        connection_quality: int
    ) -> List[str]:
        """Generate actionable recommendations for account sync"""
        
        recommendations = []
        
        if sync_health == SyncHealth.DISCONNECTED:
            recommendations.append("Connect your account to Plaid for automatic synchronization")
        
        elif sync_health == SyncHealth.CRITICAL:
            if account.last_sync_error:
                recommendations.append("Reconnect your bank account - there's a connection issue")
            else:
                recommendations.append("Your account hasn't synced in over a week - check your connection")
        
        elif sync_health == SyncHealth.WARNING:
            recommendations.append("Account sync is overdue - consider triggering a manual sync")
        
        if connection_quality < 50:
            recommendations.append("Poor connection quality - consider re-linking your account")
        
        elif connection_quality < 75:
            recommendations.append("Connection quality could be improved")
        
        if account.sync_status == 'error':
            recommendations.append("Resolve sync errors by checking your bank credentials")
        
        if not recommendations and sync_health == SyncHealth.HEALTHY:
            recommendations.append("Account is syncing properly - no action needed")
        
        return recommendations[:3]  # Return max 3 recommendations
    
    def _calculate_next_sync(self, account: Account, frequency: SyncFrequency) -> Optional[datetime]:
        """Calculate when the next sync should occur"""
        
        if not account.is_plaid_connected or frequency == SyncFrequency.MANUAL:
            return None
        
        if not account.last_sync_at:
            return datetime.now(timezone.utc)  # Sync immediately
        
        intervals = {
            SyncFrequency.HOURLY: timedelta(hours=1),
            SyncFrequency.DAILY: timedelta(days=1),
            SyncFrequency.WEEKLY: timedelta(weeks=1),
            SyncFrequency.MONTHLY: timedelta(days=30)
        }
        
        interval = intervals.get(frequency, timedelta(days=1))
        return account.last_sync_at + interval
    
    async def trigger_health_alerts(self, user_id: str, db: Session):
        """Trigger alerts for accounts with health issues"""
        
        overview = await self.get_user_sync_overview(user_id, db)
        
        if overview['accounts_needing_attention'] > 0:
            critical_accounts = [
                acc for acc in overview['accounts'] 
                if acc['sync_health'] == 'critical'
            ]
            
            warning_accounts = [
                acc for acc in overview['accounts'] 
                if acc['sync_health'] == 'warning'
            ]
            
            # Send alert notification
            await websocket_manager.send_user_event(
                user_id,
                WebSocketEvent(
                    type=EventType.SYNC_HEALTH_ALERT,
                    data={
                        'critical_accounts': len(critical_accounts),
                        'warning_accounts': len(warning_accounts),
                        'accounts_needing_attention': critical_accounts + warning_accounts,
                        'overall_health_score': overview['overall_health_score']
                    }
                )
            )

# Global monitor instance
account_sync_monitor = AccountSyncMonitor()