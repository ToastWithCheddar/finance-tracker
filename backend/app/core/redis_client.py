# backend/app/core/redis_client.py
import redis.asyncio as redis
import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for pub/sub messaging and caching"""
    
    def __init__(self):
        self.pool = None
        self._connection = None
        # BE-PERF-006: long-lived shared client used by the cache/publish helpers.
        # Reused across calls instead of opening+closing per call against the pool.
        self._shared: Optional[redis.Redis] = None
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

            # Build the shared, long-lived Redis client and use it for the ping.
            # Helper methods (publish/set_cache/get_cache/delete_cache/key_exists/
            # get_connection_stats) reuse this object so we stop paying for
            # per-call connection open/close churn against the pool.
            self._shared = redis.Redis(connection_pool=self.pool)
            await self._shared.ping()

            self._initialized = True
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            raise
            
    async def get_connection(self) -> redis.Redis:
        """Get a Redis connection from the pool.

        Used by callers that explicitly manage their own connection lifecycle
        (e.g. opening a pubsub, or grouping several commands and closing
        afterwards). Helper methods on this class instead use ``_get_shared``.
        """
        if not self._initialized:
            await self.initialize()

        return redis.Redis(connection_pool=self.pool)

    async def _get_shared(self) -> redis.Redis:
        """Return the long-lived shared Redis client (BE-PERF-006)."""
        if not self._initialized or self._shared is None:
            await self.initialize()
        return self._shared  # type: ignore[return-value]

    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a Redis channel"""
        try:
            conn = await self._get_shared()

            # Serialize message to JSON
            message_json = json.dumps({
                **message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": channel
            })

            # Publish to channel (shared connection — do not close)
            result = await conn.publish(channel, message_json)

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
                # BE-PERF-007: replace the prior `get_message(timeout=1.0)` +
                # `asyncio.sleep(0.01)` busy-poll with the native async iterator
                # supported by redis-py >= 4.2. listen() blocks on the underlying
                # socket until a message arrives, so there is no per-iteration
                # wakeup cost and no artificial 1s polling latency.
                async for message in pubsub.listen():
                    if not message or message.get("type") != "message":
                        continue
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
            conn = await self._get_shared()

            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            result = await conn.setex(key, expire_seconds, value)
            return result

        except Exception as e:
            logger.error(f"Error setting cache key '{key}': {str(e)}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from Redis cache"""
        try:
            conn = await self._get_shared()
            value = await conn.get(key)

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
            conn = await self._get_shared()
            result = await conn.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Error deleting cache key '{key}': {str(e)}")
            return False

    async def key_exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        try:
            conn = await self._get_shared()
            exists = await conn.exists(key)
            return exists > 0
        except Exception as e:
            logger.error(f"Error checking if key '{key}' exists: {str(e)}")
            return False

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get Redis connection and usage statistics"""
        try:
            conn = await self._get_shared()

            # Get Redis info
            info = await conn.info()
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting Redis stats: {str(e)}")
            return {}
    
    async def close(self):
        """Close Redis connections"""
        try:
            if self._shared is not None:
                try:
                    await self._shared.close()
                except Exception:
                    pass
                self._shared = None
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
