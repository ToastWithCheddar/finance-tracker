# backend/app/core/redis_client.py
import redis.asyncio as redis
import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for pub/sub messaging and caching"""
    
    def __init__(self):
        self.pool = None
        self._connection = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            # Create connection pool from URL
            self.pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            test_conn = redis.Redis(connection_pool=self.pool)
            await test_conn.ping()
            await test_conn.close()
            
            self._initialized = True
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            raise
            
    async def get_connection(self) -> redis.Redis:
        """Get a Redis connection from the pool"""
        if not self._initialized:
            await self.initialize()
            
        return redis.Redis(connection_pool=self.pool)
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a Redis channel"""
        try:
            conn = await self.get_connection()
            
            # Serialize message to JSON
            message_json = json.dumps({
                **message,
                "timestamp": datetime.utcnow().isoformat(),
                "channel": channel
            })
            
            # Publish to channel
            result = await conn.publish(channel, message_json)
            await conn.close()
            
            logger.debug(f"Published message to channel '{channel}': {result} subscribers")
            return result > 0
            
        except Exception as e:
            logger.error(f"Error publishing to channel '{channel}': {str(e)}")
            return False
    
    async def subscribe(
        self, 
        channel: str, 
        callback: Callable[[Dict[str, Any]], Awaitable[None]],
        error_callback: Optional[Callable[[Exception], Awaitable[None]]] = None
    ):
        """Subscribe to a Redis channel with callback"""
        try:
            conn = await self.get_connection()
            pubsub = conn.pubsub()
            
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")
            
            try:
                while True:
                    # Get message with timeout to prevent blocking
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    
                    if message and message.get("type") == "message":
                        try:
                            # Parse JSON message
                            message_data = json.loads(message["data"])
                            
                            # Call the callback
                            await callback(message_data)
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON in message from channel '{channel}': {str(e)}")
                        except Exception as e:
                            logger.error(f"Error in callback for channel '{channel}': {str(e)}")
                            if error_callback:
                                await error_callback(e)
                    
                    # Small sleep to prevent tight loop
                    await asyncio.sleep(0.01)
                    
            except asyncio.CancelledError:
                logger.info(f"Subscription to channel '{channel}' cancelled")
                raise
            except Exception as e:
                logger.error(f"Error in subscription to channel '{channel}': {str(e)}")
                if error_callback:
                    await error_callback(e)
                raise
            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
                await conn.close()
                
        except Exception as e:
            logger.error(f"Failed to subscribe to channel '{channel}': {str(e)}")
            raise
    
    async def publish_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a user-specific channel"""
        channel = f"ws:user:{user_id}"
        return await self.publish(channel, message)
    
    async def publish_to_all_users(self, message: Dict[str, Any]) -> bool:
        """Publish a message to the global broadcast channel"""
        channel = "ws:broadcast"
        return await self.publish(channel, message)
    
    async def set_cache(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """Set a value in Redis cache"""
        try:
            conn = await self.get_connection()
            
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            result = await conn.setex(key, expire_seconds, value)
            await conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error setting cache key '{key}': {str(e)}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from Redis cache"""
        try:
            conn = await self.get_connection()
            value = await conn.get(key)
            await conn.close()
            
            if value is None:
                return None
                
            # Try to parse as JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"Error getting cache key '{key}': {str(e)}")
            return None
    
    async def delete_cache(self, key: str) -> bool:
        """Delete a key from Redis cache"""
        try:
            conn = await self.get_connection()
            result = await conn.delete(key)
            await conn.close()
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error deleting cache key '{key}': {str(e)}")
            return False
    
    async def key_exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        try:
            conn = await self.get_connection()
            exists = await conn.exists(key)
            await conn.close()
            return exists > 0
        except Exception as e:
            logger.error(f"Error checking if key '{key}' exists: {str(e)}")
            return False
    
    async def persist_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Persist a message for a user (for offline recovery)"""
        try:
            conn = await self.get_connection()
            key = f"notifications:{user_id}"
            
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat()
            
            # Store as JSON in a list (FIFO queue)
            await conn.lpush(key, json.dumps(message))
            
            # Keep only last 100 messages
            await conn.ltrim(key, 0, 99)
            
            # Set expiration for 7 days
            await conn.expire(key, 7 * 24 * 3600)
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error persisting message for user '{user_id}': {str(e)}")
            return False
    
    async def get_missed_messages(self, user_id: str, limit: int = 20) -> list:
        """Get missed messages for a user"""
        try:
            conn = await self.get_connection()
            key = f"notifications:{user_id}"
            
            # Get messages from the list
            messages = await conn.lrange(key, 0, limit - 1)
            await conn.close()
            
            # Parse JSON messages
            parsed_messages = []
            for message in reversed(messages):  # Reverse to get chronological order
                try:
                    parsed_message = json.loads(message)
                    parsed_messages.append(parsed_message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in stored message for user '{user_id}'")
                    
            return parsed_messages
            
        except Exception as e:
            logger.error(f"Error getting missed messages for user '{user_id}': {str(e)}")
            return []
    
    async def cleanup_old_messages(self, max_age_hours: int = 24) -> int:
        """Cleanup old messages from all user notification queues"""
        try:
            conn = await self.get_connection()
            
            # Get all notification keys
            keys = await conn.keys("notifications:*")
            cleaned_count = 0
            
            for key in keys:
                try:
                    # Get all messages
                    messages = await conn.lrange(key, 0, -1)
                    current_time = datetime.utcnow()
                    
                    # Filter out old messages
                    valid_messages = []
                    for message in messages:
                        try:
                            parsed_message = json.loads(message)
                            message_time = datetime.fromisoformat(parsed_message.get("timestamp", ""))
                            
                            # Keep message if it's newer than max_age_hours
                            age_hours = (current_time - message_time).total_seconds() / 3600
                            if age_hours <= max_age_hours:
                                valid_messages.append(message)
                            else:
                                cleaned_count += 1
                                
                        except (json.JSONDecodeError, ValueError):
                            # Remove invalid messages
                            cleaned_count += 1
                    
                    # Replace the list with valid messages only
                    if len(valid_messages) < len(messages):
                        await conn.delete(key)
                        if valid_messages:
                            await conn.lpush(key, *valid_messages)
                            await conn.expire(key, 7 * 24 * 3600)
                            
                except Exception as e:
                    logger.error(f"Error cleaning messages for key '{key}': {str(e)}")
            
            await conn.close()
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old messages")
                
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during message cleanup: {str(e)}")
            return 0
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get Redis connection and usage statistics"""
        try:
            conn = await self.get_connection()
            
            # Get Redis info
            info = await conn.info()
            
            # Get notification queue stats
            notification_keys = await conn.keys("notifications:*")
            total_notifications = 0
            
            for key in notification_keys:
                count = await conn.llen(key)
                total_notifications += count
            
            await conn.close()
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "notification_queues": len(notification_keys),
                "total_stored_notifications": total_notifications,
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {str(e)}")
            return {}
    
    async def close(self):
        """Close Redis connections"""
        try:
            if self.pool:
                await self.pool.disconnect()
                logger.info("Redis connection pool closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {str(e)}")


# Global Redis client instance
redis_client = RedisClient()


# Dependency for FastAPI
async def get_redis_client() -> RedisClient:
    """Dependency to get Redis client instance"""
    if not redis_client._initialized:
        await redis_client.initialize()
    return redis_client