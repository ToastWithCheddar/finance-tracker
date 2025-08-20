"""
Financial Health Configuration Schema
Defines configurable parameters for financial health scoring algorithm
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any


class BalanceThresholds(BaseModel):
    """Balance-related thresholds in cents"""
    negative_penalty: int = Field(30, description="Penalty for negative balance")
    low_balance_threshold: int = Field(10000, description="Low balance threshold in cents ($100)")
    low_balance_penalty: int = Field(20, description="Penalty for low balance")
    good_balance_threshold: int = Field(100000, description="Good balance threshold in cents ($1000)")
    good_balance_bonus: int = Field(10, description="Bonus for good balance")


class ActivityThresholds(BaseModel):
    """Activity-related scoring parameters"""
    inactive_penalty: int = Field(20, description="Penalty for inactive accounts")
    high_activity_bonus: int = Field(10, description="Bonus for high activity")
    sync_hours_threshold: int = Field(24, description="Hours for recent sync bonus")
    sync_bonus: int = Field(5, description="Bonus for recently synced accounts")


class CashFlowThresholds(BaseModel):
    """Cash flow related parameters in cents"""
    positive_flow_bonus: int = Field(15, description="Bonus for positive cash flow")
    high_spending_threshold: int = Field(50000, description="High spending threshold in cents ($500)")
    high_spending_penalty: int = Field(25, description="Penalty for excessive spending")


class DebtThresholds(BaseModel):
    """Debt ratio thresholds and penalties"""
    high_debt_ratio: float = Field(0.5, description="High debt ratio threshold")
    high_debt_penalty: int = Field(30, description="Penalty for high debt ratio")
    moderate_debt_ratio: float = Field(0.3, description="Moderate debt ratio threshold")
    moderate_debt_penalty: int = Field(15, description="Penalty for moderate debt ratio")

    @validator('high_debt_ratio', 'moderate_debt_ratio')
    def validate_ratio(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Debt ratios must be between 0 and 1')
        return v


class InvestmentThresholds(BaseModel):
    """Investment ratio thresholds and bonuses"""
    min_investment_ratio: float = Field(0.1, description="Minimum investment ratio")
    min_liquid_for_investment: int = Field(100000, description="Min liquid assets for investment penalty in cents ($1000)")
    low_investment_penalty: int = Field(20, description="Penalty for low investment ratio")
    good_investment_ratio: float = Field(0.3, description="Good investment ratio threshold")
    good_investment_bonus: int = Field(10, description="Bonus for good investment ratio")

    @validator('min_investment_ratio', 'good_investment_ratio')
    def validate_ratio(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Investment ratios must be between 0 and 1')
        return v


class NetWorthThresholds(BaseModel):
    """Net worth thresholds in cents"""
    negative_net_worth_penalty: int = Field(25, description="Penalty for negative net worth")
    good_net_worth_threshold: int = Field(1000000, description="Good net worth threshold in cents ($10,000)")
    good_net_worth_bonus: int = Field(15, description="Bonus for good net worth")


class ScoringParameters(BaseModel):
    """Overall scoring parameters"""
    base_score: int = Field(100, description="Starting score for individual accounts")
    user_base_score: int = Field(70, description="Starting score for user overall health")
    min_score: int = Field(0, description="Minimum possible score")
    max_score: int = Field(100, description="Maximum possible score")
    
    # Grade thresholds
    grade_a_threshold: int = Field(90, description="Minimum score for grade A")
    grade_b_threshold: int = Field(80, description="Minimum score for grade B") 
    grade_c_threshold: int = Field(70, description="Minimum score for grade C")
    grade_d_threshold: int = Field(60, description="Minimum score for grade D")


class UserHealthThresholds(BaseModel):
    """User-level financial health thresholds"""
    positive_balance_bonus: int = Field(10, description="Bonus for positive total balance")
    high_balance_threshold: int = Field(1000000, description="High balance threshold in cents ($10,000)")
    high_balance_bonus: int = Field(10, description="Bonus for high balance")
    
    activity_bonus: int = Field(10, description="Bonus for having transactions")
    high_activity_threshold: int = Field(20, description="High activity transaction count")
    high_activity_bonus: int = Field(5, description="Bonus for high activity")
    
    analysis_period_days: int = Field(30, description="Days to look back for activity analysis")
    
    # Net worth thresholds (different from individual account)
    negative_net_worth_penalty: int = Field(20, description="User-level penalty for negative net worth")
    excellent_net_worth_threshold: int = Field(5000000, description="Excellent net worth threshold in cents ($50,000)")
    excellent_net_worth_bonus: int = Field(15, description="Bonus for excellent net worth")


class RecommendationThresholds(BaseModel):
    """Thresholds for generating recommendations"""
    emergency_fund_minimum: int = Field(100000, description="Minimum emergency fund in cents ($1,000)")
    emergency_fund_good: int = Field(500000, description="Good emergency fund in cents ($5,000)")
    
    investment_starter_liquid: int = Field(500000, description="Liquid assets to start recommending investment in cents ($5,000)")
    investment_increase_liquid: int = Field(1000000, description="Liquid assets to recommend increasing investment in cents ($10,000)")
    
    advisor_score_threshold: int = Field(60, description="Score below which to recommend financial advisor")
    excellent_score_threshold: int = Field(80, description="Score above which to congratulate user")


class FinancialHealthConfig(BaseModel):
    """Complete financial health configuration"""
    balance: BalanceThresholds = Field(default_factory=BalanceThresholds)
    activity: ActivityThresholds = Field(default_factory=ActivityThresholds)
    cash_flow: CashFlowThresholds = Field(default_factory=CashFlowThresholds)
    debt: DebtThresholds = Field(default_factory=DebtThresholds)
    investment: InvestmentThresholds = Field(default_factory=InvestmentThresholds)
    net_worth: NetWorthThresholds = Field(default_factory=NetWorthThresholds)
    scoring: ScoringParameters = Field(default_factory=ScoringParameters)
    user_health: UserHealthThresholds = Field(default_factory=UserHealthThresholds)
    recommendations: RecommendationThresholds = Field(default_factory=RecommendationThresholds)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for easy access"""
        return self.dict()

    @classmethod
    def from_env_dict(cls, env_dict: Dict[str, Any]) -> 'FinancialHealthConfig':
        """Create configuration from environment variables dictionary"""
        config_dict = {}
        
        # Map environment variables to nested structure
        for key, value in env_dict.items():
            if key.startswith('FINANCIAL_HEALTH_'):
                # Remove prefix and convert to nested dict
                config_key = key.replace('FINANCIAL_HEALTH_', '').lower()
                parts = config_key.split('_')
                
                # Build nested structure
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
        
        return cls(**config_dict)


# Default configuration instance
DEFAULT_FINANCIAL_HEALTH_CONFIG = FinancialHealthConfig()