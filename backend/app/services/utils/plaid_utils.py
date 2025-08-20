"""
Plaid utility functions
Shared helper functions for Plaid-related operations across services
"""

from typing import Dict, List
from app.models.account import Account


def group_accounts_by_token(accounts: List[Account]) -> Dict[str, List[Account]]:
    """Group accounts by their Plaid access token"""
    token_groups = {}
    for account in accounts:
        token = account.plaid_access_token
        if token not in token_groups:
            token_groups[token] = []
        token_groups[token].append(account)
    return token_groups