"""
Automatic Sync Scheduler Service
Handles scheduled synchronization of accounts and transactions
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum

from app.database import get_db
from app.models.account import Account
from app.models.user import User
from app.services.enhanced_plaid_service import enhanced_plaid_service
from app.services.transaction_sync_service import transaction_sync_service
from app.services.account_sync_monitor import account_sync_monitor
from app.services.enhanced_reconciliation_service import enhanced_reconciliation_service
from app.websocket.manager import websocket_manager
from app.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)

class SyncFrequency(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

@dataclass
class SyncJob:
    """Represents a scheduled sync job"""
    job_id: str
    account_id: str
    user_id: str
    frequency: SyncFrequency
    last_run: Optional[datetime]
    next_run: datetime
    enabled: bool
    retry_count: int
    max_retries: int = 3

class AutomaticSyncScheduler:
    """Service for managing automatic account synchronization"""
    
    def __init__(self):
        self.plaid_service = enhanced_plaid_service
        self.sync_service = transaction_sync_service
        self.monitor = account_sync_monitor
        self.reconciliation_service = enhanced_reconciliation_service
        
        # Sync configuration
        self.sync_intervals = {
            SyncFrequency.HOURLY: timedelta(hours=1),
            SyncFrequency.DAILY: timedelta(days=1),
            SyncFrequency.WEEKLY: timedelta(weeks=1),
            SyncFrequency.MONTHLY: timedelta(days=30)
        }
        
        # Active sync jobs
        self.sync_jobs: Dict[str, SyncJob] = {}
        self.is_running = False
        self.scheduler_task = None
        
        # Rate limiting
        self.max_concurrent_syncs = 5
        self.sync_semaphore = asyncio.Semaphore(self.max_concurrent_syncs)
        
        # Metrics
        self.sync_metrics = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_scheduler_run': None,
            'next_scheduler_run': None
        }
    
    async def start_scheduler(self):
        """Start the automatic sync scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Automatic sync scheduler started")
    
    async def stop_scheduler(self):
        """Stop the automatic sync scheduler"""
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Automatic sync scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                self.sync_metrics['last_scheduler_run'] = datetime.now(timezone.utc)
                
                # Load sync jobs from database
                await self._load_sync_jobs()
                
                # Execute due jobs
                await self._execute_due_jobs()
                
                # Cleanup completed jobs
                await self._cleanup_jobs()
                
                # Update next run time
                self.sync_metrics['next_scheduler_run'] = datetime.now(timezone.utc) + timedelta(minutes=15)
                
                # Sleep for 15 minutes
                await asyncio.sleep(900)  # 15 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(300)  # 5 minutes on error
    
    async def _load_sync_jobs(self):
        """Load sync jobs from database"""
        try:
            db = next(get_db())
            
            # Get all Plaid-connected accounts
            accounts = db.query(Account).filter(
                Account.plaid_access_token.isnot(None),
                Account.is_active == True
            ).all()
            
            for account in accounts:
                job_id = f"account_{account.id}"
                
                # Determine sync frequency
                frequency = self._determine_account_sync_frequency(account)
                
                # Calculate next run time
                if job_id in self.sync_jobs:
                    # Update existing job
                    job = self.sync_jobs[job_id]
                    job.frequency = frequency
                else:
                    # Create new job
                    next_run = self._calculate_next_run_time(account, frequency)
                    
                    job = SyncJob(
                        job_id=job_id,
                        account_id=str(account.id),
                        user_id=str(account.user_id),
                        frequency=frequency,
                        last_run=account.last_sync_at,
                        next_run=next_run,
                        enabled=True,
                        retry_count=0
                    )
                    
                    self.sync_jobs[job_id] = job
            
            db.close()
            
        except Exception as e:
            logger.error(f"Failed to load sync jobs: {e}")
    
    def _determine_account_sync_frequency(self, account: Account) -> SyncFrequency:
        """Determine appropriate sync frequency for an account"""
        
        # Check account metadata for user preference
        metadata = account.account_metadata or {}
        preferred_frequency = metadata.get('sync_frequency')
        
        if preferred_frequency:
            try:
                return SyncFrequency(preferred_frequency)
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
    
    def _calculate_next_run_time(self, account: Account, frequency: SyncFrequency) -> datetime:
        """Calculate next run time for an account"""
        
        base_time = account.last_sync_at or datetime.now(timezone.utc)
        interval = self.sync_intervals[frequency]
        
        # Add some jitter to prevent thundering herd
        import random
        jitter_minutes = random.randint(-30, 30)
        jitter = timedelta(minutes=jitter_minutes)
        
        return base_time + interval + jitter
    
    async def _execute_due_jobs(self):
        """Execute all jobs that are due for execution"""
        
        now = datetime.now(timezone.utc)
        due_jobs = [
            job for job in self.sync_jobs.values()
            if job.enabled and job.next_run <= now and job.retry_count < job.max_retries
        ]
        
        if not due_jobs:
            return
        
        logger.info(f"Executing {len(due_jobs)} due sync jobs")
        
        # Execute jobs with rate limiting
        tasks = []
        for job in due_jobs:
            task = asyncio.create_task(self._execute_sync_job(job))
            tasks.append(task)
        
        # Wait for all jobs to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for job, result in zip(due_jobs, results):
            if isinstance(result, Exception):
                await self._handle_job_failure(job, str(result))
            else:
                await self._handle_job_success(job, result)
    
    async def _execute_sync_job(self, job: SyncJob) -> Dict[str, Any]:
        """Execute a single sync job"""
        
        async with self.sync_semaphore:
            try:
                logger.info(f"Executing sync job for account {job.account_id}")
                
                db = next(get_db())
                
                # Step 1: Sync account balance
                balance_result = await self.plaid_service.sync_account_balances(
                    db, [job.account_id], force_sync=False
                )
                
                # Step 2: Sync transactions (last 7 days for regular sync)
                transaction_result = await self.sync_service.sync_account_transactions(
                    job.account_id, db, days=7
                )
                
                # Step 3: Perform reconciliation check
                reconciliation_result = await self.reconciliation_service.reconcile_account(
                    db, job.account_id
                )
                
                # Step 4: Update sync metrics
                await self._update_sync_metrics(job, reconciliation_result)
                
                db.close()
                
                self.sync_metrics['successful_syncs'] += 1
                
                return {
                    'status': 'success',
                    'balance_sync': balance_result,
                    'transaction_sync': {
                        'new_transactions': transaction_result.new_transactions,
                        'updated_transactions': transaction_result.updated_transactions,
                        'sync_duration': transaction_result.sync_duration_seconds
                    },
                    'reconciliation': {
                        'is_reconciled': reconciliation_result.is_reconciled,
                        'discrepancy': reconciliation_result.discrepancy,
                        'confidence_score': reconciliation_result.confidence_score
                    }
                }
                
            except Exception as e:
                logger.error(f"Sync job failed for account {job.account_id}: {e}")
                self.sync_metrics['failed_syncs'] += 1
                raise
    
    async def _handle_job_success(self, job: SyncJob, result: Dict[str, Any]):
        """Handle successful job execution"""
        
        job.last_run = datetime.now(timezone.utc)
        job.retry_count = 0
        job.next_run = job.last_run + self.sync_intervals[job.frequency]
        
        # Send success notification
        await self._send_sync_notification(job, result, success=True)
        
        logger.info(f"Sync job completed successfully for account {job.account_id}")
    
    async def _handle_job_failure(self, job: SyncJob, error: str):
        """Handle failed job execution"""
        
        job.retry_count += 1
        
        if job.retry_count >= job.max_retries:
            # Mark job as failed and disable
            job.enabled = False
            logger.error(f"Sync job permanently failed for account {job.account_id} after {job.max_retries} attempts")
            
            # Send failure notification
            await self._send_sync_notification(job, {'error': error}, success=False)
            
            # Update account status
            try:
                db = next(get_db())
                account = db.query(Account).filter(Account.id == job.account_id).first()
                if account:
                    account.sync_status = 'error'
                    account.last_sync_error = error
                    account.connection_health = 'failed'
                    db.add(account)
                    db.commit()
                db.close()
            except:
                pass
        else:
            # Schedule retry with exponential backoff
            backoff_minutes = 2 ** job.retry_count * 30  # 30, 60, 120 minutes
            job.next_run = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
            
            logger.warning(f"Sync job failed for account {job.account_id}, retrying in {backoff_minutes} minutes")
    
    async def _update_sync_metrics(self, job: SyncJob, reconciliation_result):
        """Update sync metrics for monitoring"""
        
        try:
            db = next(get_db())
            account = db.query(Account).filter(Account.id == job.account_id).first()
            
            if account:
                metadata = account.account_metadata or {}
                
                # Update sync history
                if 'sync_history' not in metadata:
                    metadata['sync_history'] = []
                
                sync_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'type': 'automatic',
                    'status': 'success',
                    'reconciliation_confidence': reconciliation_result.confidence_score,
                    'is_reconciled': reconciliation_result.is_reconciled,
                    'discrepancy': reconciliation_result.discrepancy
                }
                
                metadata['sync_history'].append(sync_entry)
                metadata['sync_history'] = metadata['sync_history'][-20:]  # Keep last 20
                
                account.account_metadata = metadata
                db.add(account)
                db.commit()
            
            db.close()
            
        except Exception as e:
            logger.error(f"Failed to update sync metrics: {e}")
    
    async def _send_sync_notification(self, job: SyncJob, result: Dict[str, Any], success: bool):
        """Send sync notification to user"""
        
        try:
            event_type = EventType.AUTOMATIC_SYNC_COMPLETE if success else EventType.AUTOMATIC_SYNC_FAILED
            
            notification_data = {
                'account_id': job.account_id,
                'sync_frequency': job.frequency.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': success
            }
            
            if success:
                notification_data.update({
                    'new_transactions': result.get('transaction_sync', {}).get('new_transactions', 0),
                    'is_reconciled': result.get('reconciliation', {}).get('is_reconciled', False),
                    'discrepancy': result.get('reconciliation', {}).get('discrepancy', 0)
                })
            else:
                notification_data['error'] = result.get('error', 'Unknown error')
            
            await websocket_manager.send_user_event(
                job.user_id,
                WebSocketEvent(
                    type=event_type,
                    data=notification_data
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to send sync notification: {e}")
    
    async def _cleanup_jobs(self):
        """Clean up old or disabled jobs"""
        
        now = datetime.now(timezone.utc)
        cleanup_cutoff = now - timedelta(days=7)  # Remove jobs older than 7 days
        
        jobs_to_remove = []
        
        for job_id, job in self.sync_jobs.items():
            # Remove permanently failed jobs after 7 days
            if not job.enabled and job.last_run and job.last_run < cleanup_cutoff:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.sync_jobs[job_id]
            logger.info(f"Cleaned up old sync job: {job_id}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        
        active_jobs = len([job for job in self.sync_jobs.values() if job.enabled])
        failed_jobs = len([job for job in self.sync_jobs.values() if not job.enabled])
        
        next_jobs = sorted(
            [job for job in self.sync_jobs.values() if job.enabled],
            key=lambda j: j.next_run
        )[:5]  # Next 5 jobs
        
        return {
            'is_running': self.is_running,
            'total_jobs': len(self.sync_jobs),
            'active_jobs': active_jobs,
            'failed_jobs': failed_jobs,
            'metrics': self.sync_metrics,
            'next_jobs': [
                {
                    'job_id': job.job_id,
                    'account_id': job.account_id,
                    'frequency': job.frequency.value,
                    'next_run': job.next_run.isoformat(),
                    'retry_count': job.retry_count
                }
                for job in next_jobs
            ]
        }
    
    async def schedule_immediate_sync(self, account_id: str, user_id: str) -> Dict[str, Any]:
        """Schedule an immediate sync for an account"""
        
        job_id = f"immediate_{account_id}_{int(datetime.now().timestamp())}"
        
        job = SyncJob(
            job_id=job_id,
            account_id=account_id,
            user_id=user_id,
            frequency=SyncFrequency.DAILY,  # Default frequency
            last_run=None,
            next_run=datetime.now(timezone.utc),
            enabled=True,
            retry_count=0
        )
        
        # Execute immediately
        try:
            result = await self._execute_sync_job(job)
            return {
                'success': True,
                'message': 'Immediate sync completed successfully',
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Immediate sync failed: {str(e)}',
                'error': str(e)
            }
    
    async def update_account_sync_frequency(
        self, 
        account_id: str, 
        frequency: str,
        db: Session
    ) -> Dict[str, Any]:
        """Update sync frequency for an account"""
        
        try:
            sync_frequency = SyncFrequency(frequency)
        except ValueError:
            return {
                'success': False,
                'message': f'Invalid frequency: {frequency}'
            }
        
        # Update account metadata
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return {
                'success': False,
                'message': 'Account not found'
            }
        
        metadata = account.account_metadata or {}
        metadata['sync_frequency'] = frequency
        account.account_metadata = metadata
        
        db.add(account)
        db.commit()
        
        # Update existing job
        job_id = f"account_{account_id}"
        if job_id in self.sync_jobs:
            job = self.sync_jobs[job_id]
            job.frequency = sync_frequency
            job.next_run = self._calculate_next_run_time(account, sync_frequency)
        
        return {
            'success': True,
            'message': f'Sync frequency updated to {frequency}'
        }

# Global scheduler instance
automatic_sync_scheduler = AutomaticSyncScheduler()