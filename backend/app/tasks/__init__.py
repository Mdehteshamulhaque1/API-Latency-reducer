"""
Celery background tasks for cache cleanup and log processing.
"""
import asyncio
import logging
from datetime import datetime, timedelta, UTC

from celery import Celery, shared_task
from sqlalchemy import select, func, delete, and_

from app.config import settings
from app.utils.redis_client import redis_client
from app.database.db import AsyncSessionLocal
from app.models import APILog, Analytics
from app.utils.logger import get_logger

# Configure Celery
celery_app = Celery(
    settings.app_name,
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

logger = get_logger(__name__)


async def _get_session():
    """Get async session."""
    return AsyncSessionLocal()


@shared_task
def cleanup_cache():
    """
    Periodic task to clean up expired cache entries.
    Scheduled to run every hour.
    """
    logger.info("Starting cache cleanup task")
    try:
        # Remove all expired cache keys from Redis
        async def _cleanup():
            if not redis_client.client:
                logger.warning("Redis client not initialized, skipping cache cleanup")
                return 0
            
            # Find all cache keys
            cache_keys = await redis_client.keys("cache:*")
            expired_count = 0
            
            for key in cache_keys:
                ttl = await redis_client.get_ttl(key)
                if ttl <= 0:  # Expired or no TTL
                    await redis_client.delete(key)
                    expired_count += 1
            
            logger.info(f"Cache cleanup: removed {expired_count} expired entries")
            return expired_count
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        removed = loop.run_until_complete(_cleanup())
        loop.close()
        
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "removed_entries": removed
        }
    except Exception as e:
        logger.error(f"Cache cleanup failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@shared_task
def aggregate_logs():
    """
    Periodic task to aggregate API logs and update analytics.
    Scheduled to run every 15 minutes.
    """
    logger.info("Starting log aggregation task")
    try:
        async def _aggregate():
            session = await _get_session()
            try:
                # Get logs from the last hour
                one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
                
                # Query recent logs
                result = await session.execute(
                    select(APILog).where(APILog.created_at >= one_hour_ago)
                )
                recent_logs = result.scalars().all()
                
                if not recent_logs:
                    logger.info("No recent logs to aggregate")
                    return 0
                
                # Calculate statistics
                total_requests = len(recent_logs)
                total_errors = sum(1 for log in recent_logs if log.status_code >= 400)
                cache_hits = sum(1 for log in recent_logs if log.cache_hit)
                cache_misses = total_requests - cache_hits
                
                response_times = [log.response_time_ms for log in recent_logs]
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                min_response_time = min(response_times) if response_times else 0
                max_response_time = max(response_times) if response_times else 0
                
                total_bytes_sent = sum(log.response_size_bytes for log in recent_logs)
                total_bytes_received = sum(log.request_size_bytes for log in recent_logs)
                
                # Create analytics record
                analytics = Analytics(
                    period="hourly",
                    total_requests=total_requests,
                    total_errors=total_errors,
                    cache_hits=cache_hits,
                    cache_misses=cache_misses,
                    avg_response_time_ms=avg_response_time,
                    min_response_time_ms=min_response_time,
                    max_response_time_ms=max_response_time,
                    total_bytes_sent=total_bytes_sent,
                    total_bytes_received=total_bytes_received,
                )
                
                session.add(analytics)
                await session.commit()
                logger.info(f"Aggregated {total_requests} logs into analytics")
                return total_requests
                
            finally:
                await session.close()
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(_aggregate())
        loop.close()
        
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "logs_processed": count
        }
    except Exception as e:
        logger.error(f"Log aggregation failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@shared_task
def generate_performance_alerts():
    """
    Periodic task to generate alerts for performance degradation.
    Scheduled to run every 30 minutes.
    """
    logger.info("Starting performance alert generation")
    try:
        async def _generate_alerts():
            session = await _get_session()
            try:
                # Get latest analytics
                result = await session.execute(
                    select(Analytics).order_by(Analytics.created_at.desc()).limit(10)
                )
                recent_analytics = result.scalars().all()
                
                alerts = []
                
                if not recent_analytics:
                    return alerts
                
                # Check for performance degradation
                latest = recent_analytics[0]
                
                # Alert thresholds
                ERROR_RATE_THRESHOLD = 0.05  # 5%
                RESPONSE_TIME_THRESHOLD = 1000  # ms
                
                if latest.total_requests > 0:
                    error_rate = latest.total_errors / latest.total_requests
                    if error_rate > ERROR_RATE_THRESHOLD:
                        alerts.append({
                            "type": "high_error_rate",
                            "message": f"Error rate is {error_rate*100:.1f}%",
                            "severity": "warning" if error_rate < 0.1 else "critical",
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                
                if latest.avg_response_time_ms > RESPONSE_TIME_THRESHOLD:
                    alerts.append({
                        "type": "high_latency",
                        "message": f"Average response time is {latest.avg_response_time_ms:.0f}ms",
                        "severity": "warning",
                        "timestamp": datetime.now(UTC).isoformat()
                    })
                
                cache_hit_rate = (
                    latest.cache_hits / (latest.cache_hits + latest.cache_misses)
                    if (latest.cache_hits + latest.cache_misses) > 0
                    else 0
                )
                
                if cache_hit_rate < 0.3:  # Low cache hit rate
                    alerts.append({
                        "type": "low_cache_hit_rate",
                        "message": f"Cache hit rate is {cache_hit_rate*100:.1f}%",
                        "severity": "info",
                        "timestamp": datetime.now(UTC).isoformat()
                    })
                
                logger.info(f"Generated {len(alerts)} performance alerts")
                return alerts
                
            finally:
                await session.close()
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        alerts = loop.run_until_complete(_generate_alerts())
        loop.close()
        
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "alerts_generated": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Alert generation failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@shared_task
def cleanup_old_logs():
    """
    Periodic task to archive and delete old API logs.
    Scheduled to run daily.
    """
    logger.info("Starting old logs cleanup")
    try:
        async def _cleanup_old():
            session = await _get_session()
            try:
                # Find logs older than 90 days
                cutoff_date = datetime.now(UTC) - timedelta(days=90)
                
                # Delete old logs
                stmt = delete(APILog).where(APILog.created_at < cutoff_date)
                result = await session.execute(stmt)
                await session.commit()
                
                logger.info(f"Deleted {result.rowcount} logs older than 90 days")
                return result.rowcount
                
            finally:
                await session.close()
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        deleted = loop.run_until_complete(_cleanup_old())
        loop.close()
        
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "deleted_logs": deleted
        }
    except Exception as e:
        logger.error(f"Old logs cleanup failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


# Celery beat schedule
celery_app.conf.beat_schedule = {
    'cleanup-cache': {
        'task': 'app.tasks.cleanup_cache',
        'schedule': timedelta(hours=1),
    },
    'aggregate-logs': {
        'task': 'app.tasks.aggregate_logs',
        'schedule': timedelta(minutes=15),
    },
    'generate-alerts': {
        'task': 'app.tasks.generate_performance_alerts',
        'schedule': timedelta(minutes=30),
    },
    'cleanup-old-logs': {
        'task': 'app.tasks.cleanup_old_logs',
        'schedule': timedelta(days=1),
    },
}
