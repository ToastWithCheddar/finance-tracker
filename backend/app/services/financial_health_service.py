"""
Financial Health Service
Restored minimal implementation used by routes and websockets.
Calculates basic financial health metrics and grades without AI features.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.financial_health_config import FinancialHealthConfig, DEFAULT_FINANCIAL_HEALTH_CONFIG
from app.schemas.account_health import AccountHealthData, ReconciliationHealth, ConnectionHealth

logger = logging.getLogger(__name__)


class FinancialHealthService:
    """Service for calculating financial health metrics and scores."""

    def __init__(self, config: Optional[FinancialHealthConfig] = None):
        self.config = config or DEFAULT_FINANCIAL_HEALTH_CONFIG

    def calculate_user_financial_health(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Compute user-level financial health and simple recommendations."""
        # Gather accounts
        accounts = db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True,
        ).all()

        if not accounts:
            return {
                "overall_score": 0,
                "grade": "N/A",
                "net_worth": 0,
                "total_liquid": 0,
                "total_debt": 0,
                "total_investment": 0,
                "debt_ratio": 0,
                "investment_ratio": 0,
                "account_count": 0,
                "recent_activity": 0,
                "recommendations": [
                    "Connect your accounts to see financial health metrics",
                ],
            }

        # Basic totals
        total_liquid = sum(
            (acc.balance_cents / 100)
            for acc in accounts
            if acc.account_type in ["checking", "savings"] and (acc.balance_cents / 100) > 0
        )
        total_debt = sum(
            abs(acc.balance_cents / 100)
            for acc in accounts
            if acc.account_type in ["credit_card", "loan"] and (acc.balance_cents / 100) < 0
        )
        total_investment = sum(
            (acc.balance_cents / 100)
            for acc in accounts
            if acc.account_type in ["investment", "retirement"] and (acc.balance_cents / 100) > 0
        )
        net_worth = total_liquid + total_investment - total_debt

        # Recent activity
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= thirty_days_ago.date(),
        ).count()

        # Ratios
        debt_ratio = total_debt / max(1, total_liquid) if total_liquid > 0 else 0
        invest_base = total_liquid + total_investment
        investment_ratio = total_investment / max(1, invest_base) if invest_base > 0 else 0

        # Simple scoring using config thresholds
        score = self.config.scoring.user_base_score
        # Balance/net worth
        if net_worth < 0:
            score -= self.config.user_health.negative_net_worth_penalty
        elif net_worth > (self.config.user_health.excellent_net_worth_threshold / 100):
            score += self.config.user_health.excellent_net_worth_bonus
        # Debt
        if debt_ratio > self.config.debt.high_debt_ratio:
            score -= self.config.debt.high_debt_penalty
        elif debt_ratio > self.config.debt.moderate_debt_ratio:
            score -= self.config.debt.moderate_debt_penalty
        # Investment
        if investment_ratio > self.config.investment.good_investment_ratio:
            score += self.config.investment.good_investment_bonus
        elif investment_ratio > self.config.investment.min_investment_ratio:
            score += max(0, self.config.investment.good_investment_bonus - 5)
        # Activity
        if recent_transactions > 0:
            score += self.config.user_health.activity_bonus
        if recent_transactions > self.config.user_health.high_activity_threshold:
            score += self.config.user_health.high_activity_bonus

        score = max(self.config.scoring.min_score, min(self.config.scoring.max_score, score))
        grade = self._calculate_health_grade(score)

        # Basic recommendations
        recs: List[str] = []
        if debt_ratio > self.config.debt.moderate_debt_ratio:
            recs.append("Monitor debt levels and consider payoff strategies")
        if investment_ratio < self.config.investment.min_investment_ratio and total_liquid > (
            self.config.recommendations.investment_starter_liquid / 100
        ):
            recs.append("Consider starting or increasing investments for long-term growth")
        if total_liquid < (self.config.recommendations.emergency_fund_minimum / 100):
            recs.append("Build an emergency fund of at least $1,000")

        return {
            "overall_score": score,
            "grade": grade,
            "net_worth": net_worth,
            "total_liquid": total_liquid,
            "total_debt": total_debt,
            "total_investment": total_investment,
            "debt_ratio": debt_ratio,
            "investment_ratio": investment_ratio,
            "account_count": len(accounts),
            "recent_activity": recent_transactions,
            "recommendations": recs,
        }

    def calculate_overall_financial_health(self, categorization: Dict[str, Any]) -> Dict[str, Any]:
        """Compute overall metrics from a categorization structure (minimal)."""
        categories = categorization.get("categories", {})
        liquid = [
            acc.get("balance", 0)
            for acc in (categories.get("spending", []) + categories.get("saving", []))
            if acc.get("balance", 0) > 0
        ]
        total_liquid = sum(liquid)
        total_debt = sum(
            abs(acc.get("balance", 0)) for acc in categories.get("credit", []) if acc.get("balance", 0) < 0
        )
        total_investment = sum(
            acc.get("balance", 0) for acc in categories.get("investment", []) if acc.get("balance", 0) > 0
        )
        net_worth = total_liquid + total_investment - total_debt
        debt_ratio = total_debt / max(1, total_liquid) if total_liquid > 0 else 0
        invest_base = total_liquid + total_investment
        investment_ratio = total_investment / max(1, invest_base) if invest_base > 0 else 0

        score = self.config.scoring.base_score
        if debt_ratio > self.config.debt.high_debt_ratio:
            score -= self.config.debt.high_debt_penalty
        elif debt_ratio > self.config.debt.moderate_debt_ratio:
            score -= self.config.debt.moderate_debt_penalty
        if investment_ratio > self.config.investment.good_investment_ratio:
            score += self.config.investment.good_investment_bonus
        elif (
            investment_ratio < self.config.investment.min_investment_ratio
            and total_liquid > self.config.investment.min_liquid_for_investment / 100
        ):
            score -= self.config.investment.low_investment_penalty
        if net_worth < 0:
            score -= self.config.net_worth.negative_net_worth_penalty
        elif net_worth > self.config.net_worth.good_net_worth_threshold / 100:
            score += self.config.net_worth.good_net_worth_bonus

        score = max(self.config.scoring.min_score, min(self.config.scoring.max_score, score))
        grade = self._calculate_health_grade(score)

        return {
            "overall_score": score,
            "grade": grade,
            "net_worth": net_worth,
            "total_liquid": total_liquid,
            "total_debt": total_debt,
            "total_investment": total_investment,
            "debt_ratio": debt_ratio,
            "investment_ratio": investment_ratio,
            "account_diversity": len([c for c in categories.values() if c]),
            "recommendations": [],
        }

    def calculate_account_health(self, account: Account, reconciliation: Dict[str, Any]) -> AccountHealthData:
        """Compute account-level health details used by the /accounts/.../health endpoint."""
        # Reconciliation
        recon = ReconciliationHealth(
            is_reconciled=bool(reconciliation.get("is_reconciled", False)),
            discrepancy=float(reconciliation.get("discrepancy", 0) or 0),
            last_reconciliation=reconciliation.get("reconciliation_date"),
            transaction_count=int(reconciliation.get("transaction_count", 0) or 0),
        )

        # Connection health (very simple heuristic)
        metadata = getattr(account, "account_metadata", None) or {}
        last_sync = metadata.get("last_sync")
        if getattr(account, "plaid_access_token", None):
            health_status = "healthy" if last_sync else "warning"
            sync_frequency = "daily"
        else:
            health_status = "not_connected"
            sync_frequency = None
        conn = ConnectionHealth(
            health_status=health_status,
            is_plaid_connected=bool(getattr(account, "plaid_access_token", None)),
            last_sync=last_sync,
            sync_frequency=sync_frequency,
        )

        # Compute health score
        score = self.config.scoring.base_score
        if not recon.is_reconciled:
            score -= 15
        if recon.discrepancy and recon.discrepancy > 0:
            score -= 10
        if conn.health_status in ("warning", "not_connected"):
            score -= 10
        if (account.balance_cents or 0) < 0:
            score -= self.config.balance.negative_penalty
        score = max(self.config.scoring.min_score, min(self.config.scoring.max_score, score))

        recommendations: List[str] = []
        if not recon.is_reconciled:
            recommendations.append("Reconcile account to resolve discrepancies")
        if conn.health_status != "healthy":
            recommendations.append("Connect and sync your account regularly for up-to-date data")
        if (account.balance_cents or 0) < 0:
            recommendations.append("Address negative balance to improve account health")

        return AccountHealthData(
            account_id=account.id,
            account_name=account.name,
            account_type=account.account_type,
            is_active=account.is_active,
            current_balance=(account.balance_cents or 0) / 100,
            currency=account.currency,
            reconciliation=recon,
            connection=conn,
            health_score=score,
            recommendations=recommendations,
        )

    def _calculate_health_grade(self, score: int) -> str:
        if score >= self.config.scoring.grade_a_threshold:
            return "A"
        if score >= self.config.scoring.grade_b_threshold:
            return "B"
        if score >= self.config.scoring.grade_c_threshold:
            return "C"
        if score >= self.config.scoring.grade_d_threshold:
            return "D"
        return "F"


_singleton: Optional[FinancialHealthService] = None


def get_financial_health_service(config: Optional[FinancialHealthConfig] = None) -> FinancialHealthService:
    global _singleton
    if _singleton is None or config is not None:
        _singleton = FinancialHealthService(config)
    return _singleton

