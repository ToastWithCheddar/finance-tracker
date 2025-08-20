"""
Service for automated transaction categorization using rules
Provides efficient rule matching and application engine
"""

import logging
import re
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from uuid import UUID
from collections import defaultdict
from cachetools import TTLCache

from app.config import settings

from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

class AutoCategorizationService(BaseService):
    """Service for automated transaction categorization using rules"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        # Cache compiled rules for performance with TTL to prevent memory leaks
        self._rule_cache: TTLCache[str, List] = TTLCache(
            maxsize=settings.RULE_CACHE_MAX_SIZE,
            ttl=settings.RULE_CACHE_TTL
        )
        
    def apply_rules_to_transaction(
        self, 
        transaction: Transaction, 
        user_id: UUID,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Apply categorization rules to a single transaction"""
        
        try:
            # Get user's active rules sorted by priority
            rules = self._get_user_rules(user_id)
            
            if not rules:
                return {
                    "success": True,
                    "rule_applied": False,
                    "message": "No active rules found",
                    "changes": {}
                }
            
            # Find the first matching rule
            matching_rule = None
            for rule in rules:
                if self._rule_matches_transaction(rule, transaction):
                    matching_rule = rule
                    break
            
            if not matching_rule:
                return {
                    "success": True,
                    "rule_applied": False,
                    "message": "No matching rules found",
                    "changes": {}
                }
            
            # Apply the rule actions
            changes = {}
            applied_actions = []
            
            if not dry_run:
                changes = self._apply_rule_actions(matching_rule, transaction)
                applied_actions = list(changes.keys())
                
                # Update rule performance tracking
                matching_rule.increment_application_count()
                self.db.add(matching_rule)
                self.db.add(transaction)
                self.db.commit()
            else:
                # For dry run, just show what would change
                changes = self._preview_rule_actions(matching_rule, transaction)
            
            return {
                "success": True,
                "rule_applied": True,
                "rule_id": str(matching_rule.id),
                "rule_name": matching_rule.name,
                "applied_actions": applied_actions,
                "changes": changes,
                "dry_run": dry_run
            }
            
        except Exception as e:
            logger.error(f"Failed to apply rules to transaction {transaction.id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "rule_applied": False,
                "changes": {}
            }
    
    def batch_apply_rules(
        self, 
        transaction_ids: List[UUID], 
        user_id: UUID,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Apply rules to multiple transactions efficiently"""
        
        try:
            # Batch load transactions
            transactions = self.db.query(Transaction).filter(
                and_(
                    Transaction.id.in_(transaction_ids),
                    Transaction.user_id == user_id
                )
            ).all()
            
            if not transactions:
                return {
                    "success": True,
                    "transactions_processed": 0,
                    "rules_applied": 0,
                    "results": []
                }
            
            # Get user's rules once
            rules = self._get_user_rules(user_id)
            
            results = []
            rules_applied_count = 0
            transactions_changed = []
            
            for transaction in transactions:
                # Find matching rule
                matching_rule = None
                for rule in rules:
                    if self._rule_matches_transaction(rule, transaction):
                        matching_rule = rule
                        break
                
                if matching_rule:
                    # Apply rule actions
                    if not dry_run:
                        changes = self._apply_rule_actions(matching_rule, transaction)
                        matching_rule.increment_application_count()
                        transactions_changed.append(transaction)
                    else:
                        changes = self._preview_rule_actions(matching_rule, transaction)
                    
                    results.append({
                        "transaction_id": str(transaction.id),
                        "rule_applied": True,
                        "rule_id": str(matching_rule.id),
                        "rule_name": matching_rule.name,
                        "changes": changes
                    })
                    rules_applied_count += 1
                else:
                    results.append({
                        "transaction_id": str(transaction.id),
                        "rule_applied": False,
                        "message": "No matching rules found"
                    })
            
            # Batch commit changes
            if not dry_run and transactions_changed:
                self.db.add_all(transactions_changed)
                self.db.add_all(rules)  # For updated application counts
                self.db.commit()
            
            return {
                "success": True,
                "transactions_processed": len(transactions),
                "rules_applied": rules_applied_count,
                "results": results,
                "dry_run": dry_run
            }
            
        except Exception as e:
            logger.error(f"Failed to batch apply rules: {e}")
            if not dry_run:
                self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "transactions_processed": 0,
                "rules_applied": 0,
                "results": []
            }
    
    def test_rule_against_transactions(
        self, 
        rule_conditions: Dict[str, Any], 
        user_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Test rule conditions against user's historical transactions"""
        
        try:
            # Create a temporary rule object for testing
            temp_rule = CategorizationRule(
                user_id=user_id,
                name="Test Rule",
                conditions=rule_conditions,
                actions={},  # Not needed for testing
                priority=100
            )
            
            # Get recent transactions for user
            transactions = self.db.query(Transaction).filter(
                Transaction.user_id == user_id
            ).order_by(desc(Transaction.transaction_date)).limit(limit).all()
            
            matching_transactions = []
            for transaction in transactions:
                if self._rule_matches_transaction(temp_rule, transaction):
                    matching_transactions.append({
                        "transaction_id": str(transaction.id),
                        "description": transaction.description,
                        "merchant": transaction.merchant,
                        "amount_cents": transaction.amount_cents,
                        "amount_dollars": transaction.amount_dollars,
                        "transaction_date": transaction.transaction_date.isoformat(),
                        "current_category_id": str(transaction.category_id) if transaction.category_id else None,
                        "account_type": transaction.account.account_type if transaction.account else None
                    })
            
            return matching_transactions
            
        except Exception as e:
            logger.error(f"Failed to test rule conditions: {e}")
            return []
    
    def _get_user_rules(self, user_id: UUID) -> List[CategorizationRule]:
        """Get user's active rules sorted by priority, with caching"""
        
        cache_key = f"user_rules_{user_id}"
        
        # Check cache
        if cache_key in self._rule_cache:
            return self._rule_cache[cache_key]
        
        # Load from database
        rules = self.db.query(CategorizationRule).filter(
            and_(
                CategorizationRule.user_id == user_id,
                CategorizationRule.is_active == True
            )
        ).order_by(CategorizationRule.priority.asc()).all()
        
        # Update cache
        self._rule_cache[cache_key] = rules
        
        return rules
    
    def _rule_matches_transaction(self, rule: CategorizationRule, transaction: Transaction) -> bool:
        """Check if a rule matches a transaction"""
        
        try:
            # Check merchant conditions
            if not rule.matches_merchant(transaction.merchant, transaction.description):
                return False
            
            # Check description conditions
            if not rule.matches_description(transaction.description):
                return False
            
            # Check amount conditions
            if not rule.matches_amount(abs(transaction.amount_cents)):
                return False
            
            # Check account type conditions
            if transaction.account and not rule.matches_account_type(transaction.account.account_type):
                return False
            
            # Check transaction type conditions
            if not rule.matches_transaction_type(transaction.transaction_type):
                return False
            
            # Check account ID conditions
            if not rule.matches_account_id(transaction.account_id):
                return False
            
            # Check category exclusion conditions
            if rule.exclude_category(transaction.category_id):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rule match for rule {rule.id} and transaction {transaction.id}: {e}")
            return False
    
    def _apply_rule_actions(self, rule: CategorizationRule, transaction: Transaction) -> Dict[str, Any]:
        """Apply rule actions to a transaction"""
        
        changes = {}
        
        # Set category
        target_category_id = rule.get_target_category_id()
        if target_category_id and target_category_id != transaction.category_id:
            old_category_id = transaction.category_id
            transaction.category_id = target_category_id
            changes["category_id"] = {
                "old": str(old_category_id) if old_category_id else None,
                "new": str(target_category_id)
            }
        
        # Set confidence score
        confidence_score = rule.get_confidence_score()
        if confidence_score is not None:
            old_confidence = getattr(transaction, 'ml_confidence', None)
            transaction.ml_confidence = confidence_score
            changes["ml_confidence"] = {
                "old": old_confidence,
                "new": confidence_score
            }
        
        # Add tags
        tags_to_add = rule.get_tags_to_add()
        if tags_to_add:
            current_tags = transaction.tags or []
            new_tags = list(set(current_tags + tags_to_add))
            if new_tags != current_tags:
                transaction.tags = new_tags
                changes["tags"] = {
                    "old": current_tags,
                    "new": new_tags,
                    "added": tags_to_add
                }
        
        # Add note
        note_to_add = rule.get_note_to_add()
        if note_to_add:
            old_notes = transaction.notes or ""
            new_notes = f"{old_notes}\n{note_to_add}".strip()
            transaction.notes = new_notes
            changes["notes"] = {
                "old": old_notes,
                "new": new_notes,
                "added": note_to_add
            }
        
        # Mark as auto-categorized
        transaction.is_manually_categorized = False
        changes["auto_categorized"] = True
        
        return changes
    
    def _preview_rule_actions(self, rule: CategorizationRule, transaction: Transaction) -> Dict[str, Any]:
        """Preview what actions would be applied without making changes"""
        
        changes = {}
        
        # Preview category change
        target_category_id = rule.get_target_category_id()
        if target_category_id and target_category_id != transaction.category_id:
            changes["category_id"] = {
                "old": str(transaction.category_id) if transaction.category_id else None,
                "new": str(target_category_id)
            }
        
        # Preview confidence score change
        confidence_score = rule.get_confidence_score()
        if confidence_score is not None:
            changes["ml_confidence"] = {
                "old": getattr(transaction, 'ml_confidence', None),
                "new": confidence_score
            }
        
        # Preview tags addition
        tags_to_add = rule.get_tags_to_add()
        if tags_to_add:
            current_tags = transaction.tags or []
            new_tags = list(set(current_tags + tags_to_add))
            if new_tags != current_tags:
                changes["tags"] = {
                    "old": current_tags,
                    "new": new_tags,
                    "added": tags_to_add
                }
        
        # Preview note addition
        note_to_add = rule.get_note_to_add()
        if note_to_add:
            changes["notes"] = {
                "old": transaction.notes or "",
                "new": f"{transaction.notes or ''}\n{note_to_add}".strip(),
                "added": note_to_add
            }
        
        return changes
    
    def get_rule_effectiveness(self, rule_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Calculate how effective a rule has been"""
        
        rule = self.db.query(CategorizationRule).filter(
            and_(
                CategorizationRule.id == rule_id,
                CategorizationRule.user_id == user_id
            )
        ).first()
        
        if not rule:
            return {"error": "Rule not found"}
        
        # Calculate effectiveness metrics
        effectiveness = {
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "times_applied": rule.times_applied,
            "success_rate": rule.success_rate,
            "success_rate_percentage": rule.success_rate_percentage,
            "last_applied_at": rule.last_applied_at.isoformat() if rule.last_applied_at else None,
            "is_active": rule.is_active,
            "priority": rule.priority
        }
        
        # Find transactions that were categorized by this rule
        # This would require additional tracking in the transaction model
        # For now, we'll return the basic metrics
        
        return effectiveness
    
    def clear_rule_cache(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Clear the rule cache for a specific user or all users"""
        
        if user_id:
            cache_key = f"user_rules_{user_id}"
            entries_cleared = 1 if cache_key in self._rule_cache else 0
            if cache_key in self._rule_cache:
                del self._rule_cache[cache_key]
            
            logger.info(f"Cleared rule cache for user {user_id}")
            return {
                'success': True,
                'entries_cleared': entries_cleared,
                'message': f'Cleared rule cache for user {user_id}'
            }
        else:
            entries_cleared = len(self._rule_cache)
            self._rule_cache.clear()
            
            logger.info(f"Cleared rule cache for all users ({entries_cleared} entries)")
            return {
                'success': True,
                'entries_cleared': entries_cleared,
                'message': f'Cleared rule cache for all users ({entries_cleared} entries)'
            }
    
    def get_rule_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            'cache_size': len(self._rule_cache),
            'cache_max_size': self._rule_cache.maxsize,
            'cache_ttl_seconds': self._rule_cache.ttl
        }
    
    def get_matching_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """Get statistics about rule matching for a user"""
        
        rules = self._get_user_rules(user_id)
        
        if not rules:
            return {
                "total_rules": 0,
                "active_rules": 0,
                "total_applications": 0,
                "rules_never_used": 0,
                "average_success_rate": 0.0
            }
        
        total_applications = sum(rule.times_applied for rule in rules)
        rules_never_used = len([rule for rule in rules if rule.times_applied == 0])
        
        # Calculate average success rate for rules that have been used
        used_rules = [rule for rule in rules if rule.times_applied > 0 and rule.success_rate is not None]
        average_success_rate = (
            sum(rule.success_rate for rule in used_rules) / len(used_rules)
            if used_rules else 0.0
        )
        
        return {
            "total_rules": len(rules),
            "active_rules": len([rule for rule in rules if rule.is_active]),
            "total_applications": total_applications,
            "rules_never_used": rules_never_used,
            "average_success_rate": average_success_rate,
            "average_success_rate_percentage": average_success_rate * 100,
            "most_used_rule": {
                "id": str(max(rules, key=lambda r: r.times_applied).id),
                "name": max(rules, key=lambda r: r.times_applied).name,
                "times_applied": max(rules, key=lambda r: r.times_applied).times_applied
            } if rules else None
        }