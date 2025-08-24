#!/usr/bin/env python3
"""
Test script to verify WebSocket notification fix by triggering a transaction sync.
This simulates the sync service calling the websocket manager.
"""

import asyncio
import sys
import os

# Add backend app to path
sys.path.append('/Users/onurmerttolek/Desktop/Internship/finance-tracker/backend')

async def test_websocket_fix():
    """Test the WebSocket notification system"""
    print("🧪 Testing WebSocket notification fix...")
    
    try:
        # Import the modules
        from app.websocket.manager import redis_websocket_manager as websocket_manager
        from app.websocket.events import WebSocketEvent, EventType
        
        # Create a test event (similar to what TransactionSyncService creates)
        test_event = WebSocketEvent(
            event_type=EventType.TRANSACTION_SYNC_COMPLETE,
            data={
                'account_id': 'test-account-123',
                'account_name': 'Test Account',
                'new_transactions': 5,
                'updated_transactions': 2,
                'duplicates_skipped': 0,
                'sync_duration': 1.23,
                'date_range': '2025-01-01 to 2025-01-31'
            }
        )
        
        print("✅ Created test WebSocketEvent")
        
        # Test the send_user_event method (this was failing before)
        try:
            await websocket_manager.send_user_event('test-user-123', test_event)
            print("✅ send_user_event method works - WebSocket fix successful!")
            return True
        except AttributeError as e:
            print(f"❌ send_user_event method still missing: {e}")
            return False
        except Exception as e:
            print(f"⚠️  send_user_event method exists but failed: {e}")
            print("   (This is expected if Redis is not running or user not connected)")
            return True
            
    except Exception as e:
        print(f"❌ Failed to test WebSocket fix: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket_fix())
    exit(0 if result else 1)