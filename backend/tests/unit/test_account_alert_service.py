"""
Unit tests for AccountAlertService
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.services.account_alert_service import AccountAlertService
from app.models.account import Account
from app.models.notification import NotificationType, NotificationPriority


class TestAccountAlertService:
    """Test cases for AccountAlertService"""

    def setup_method(self):
        """Set up test dependencies"""
        self.alert_service = AccountAlertService()
        self.mock_db = MagicMock()
        self.user_id = uuid4()
        self.account_id = uuid4()

    def create_test_account(self, account_type="checking", balance_cents=5000):
        """Helper to create test account"""
        return Account(
            id=self.account_id,
            user_id=self.user_id,
            name="Test Account",
            account_type=account_type,
            balance_cents=balance_cents,
            currency="USD"
        )

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_sends_notification_when_below_threshold(self):
        """Test that notification is sent when balance is below threshold"""
        # Arrange
        account = self.create_test_account(balance_cents=5000)  # $50

        with patch('app.core.redis_client.redis_client.key_exists', new_callable=AsyncMock, return_value=False), \
             patch('app.core.redis_client.redis_client.set_cache', new_callable=AsyncMock) as mock_set_cache:
            
            # Mock the dependencies
            self.alert_service.notification_service.create_notification = AsyncMock()

            # Act
            result = await self.alert_service.check_low_balance_alert(self.mock_db, account)

            # Assert
            assert result is True
            self.alert_service.notification_service.create_notification.assert_called_once()
            
            # Verify notification details
            call_args = self.alert_service.notification_service.create_notification.call_args
            assert call_args[1]['user_id'] == self.user_id
            assert call_args[1]['type'] == NotificationType.LOW_BALANCE_WARNING
            assert call_args[1]['priority'] == NotificationPriority.HIGH
            assert "Test Account" in call_args[1]['title']
            assert "$50.00" in call_args[1]['message']
            assert "$100.00" in call_args[1]['message']
            assert call_args[1]['action_url'] == f"/accounts/{self.account_id}"

            # Verify Redis cooldown was set
            mock_set_cache.assert_called_once_with(
                f"low_balance_alert:{self.account_id}", 
                "sent", 
                expire_seconds=86400
            )

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_no_notification_when_above_threshold(self):
        """Test that no notification is sent when balance is above threshold"""
        # Arrange
        account = self.create_test_account(balance_cents=15000)  # $150

        with patch('app.core.redis_client.redis_client.key_exists', new_callable=AsyncMock, return_value=False):
            
            self.alert_service.notification_service.create_notification = AsyncMock()

            # Act
            result = await self.alert_service.check_low_balance_alert(self.mock_db, account)

            # Assert
            assert result is False
            self.alert_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_skips_when_cooldown_active(self):
        """Test that alert is skipped when cooldown key exists in Redis"""
        # Arrange
        account = self.create_test_account(balance_cents=5000)  # $50

        with patch('app.core.redis_client.redis_client.key_exists', new_callable=AsyncMock, return_value=True):
            
            self.alert_service.notification_service.create_notification = AsyncMock()

            # Act
            result = await self.alert_service.check_low_balance_alert(self.mock_db, account)

            # Assert
            assert result is None
            self.alert_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_skips_non_depository_accounts(self):
        """Test that alerts are skipped for non-depository accounts"""
        # Arrange
        account = self.create_test_account(account_type="credit_card", balance_cents=5000)

        self.alert_service.notification_service.create_notification = AsyncMock()

        # Act
        result = await self.alert_service.check_low_balance_alert(self.mock_db, account)

        # Assert
        assert result is None
        self.alert_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_skips_zero_or_negative_balance(self):
        """Test that alerts are skipped for zero or negative balances"""
        # Arrange
        account = self.create_test_account(balance_cents=0)  # $0

        with patch('app.core.redis_client.redis_client.key_exists', new_callable=AsyncMock, return_value=False):
            
            self.alert_service.notification_service.create_notification = AsyncMock()

            # Act
            result = await self.alert_service.check_low_balance_alert(self.mock_db, account)

            # Assert
            assert result is False
            self.alert_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_handles_exceptions(self):
        """Test that exceptions are properly handled and logged"""
        # Arrange
        account = self.create_test_account(balance_cents=5000)

        with patch('app.core.redis_client.redis_client.key_exists', new_callable=AsyncMock, side_effect=Exception("Redis error")):

            # Act
            result = await self.alert_service.check_low_balance_alert(self.mock_db, account)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_eligible_account_types(self):
        """Test that only checking and savings accounts are eligible"""
        eligible_types = ["checking", "savings"]
        ineligible_types = ["credit_card", "investment", "loan", "mortgage"]

        with patch('app.core.redis_client.redis_client.key_exists', new_callable=AsyncMock, return_value=False):
            
            self.alert_service.notification_service.create_notification = AsyncMock()

            # Test eligible types
            for account_type in eligible_types:
                account = self.create_test_account(account_type=account_type, balance_cents=5000)
                result = await self.alert_service.check_low_balance_alert(self.mock_db, account)
                assert result is True, f"Account type {account_type} should be eligible"

            # Reset mock
            self.alert_service.notification_service.create_notification.reset_mock()

            # Test ineligible types
            for account_type in ineligible_types:
                account = self.create_test_account(account_type=account_type, balance_cents=5000)
                result = await self.alert_service.check_low_balance_alert(self.mock_db, account)
                assert result is None, f"Account type {account_type} should not be eligible"

            # Verify no notifications were sent for ineligible types
            self.alert_service.notification_service.create_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_low_balance_alert_notification_extra_data(self):
        """Test that notification includes correct extra_data"""
        # Arrange
        account = self.create_test_account(balance_cents=7500)  # $75

        with patch('app.core.redis_client.redis_client.key_exists', new_callable=AsyncMock, return_value=False), \
             patch('app.core.redis_client.redis_client.set_cache', new_callable=AsyncMock):
            
            self.alert_service.notification_service.create_notification = AsyncMock()

            # Act
            await self.alert_service.check_low_balance_alert(self.mock_db, account)

            # Assert
            call_args = self.alert_service.notification_service.create_.call_args
            extra_data = call_args[1]['extra_data']
            
            assert extra_data['account_id'] == str(self.account_id)
            assert extra_data['account_name'] == "Test Account"
            assert extra_data['balance_cents'] == 7500
            assert extra_data['threshold_cents'] == 10000
            assert extra_data['balance_dollars'] == 75.0
            assert extra_data['threshold_dollars'] == 100.0
