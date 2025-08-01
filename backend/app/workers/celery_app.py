"""
Celery application configuration for background task processing.

Configured for high-throughput webhook event processing with 1000+ events/minute capacity.
"""

import logging
from celery import Celery
from celery.signals import setup_logging

from app.core.config import settings

# Configure Celery logging
@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    from app.core.logging import LOGGING_CONFIG
    dictConfig(LOGGING_CONFIG)

# Create Celery application
celery_app = Celery(
    "sprint_reports_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.webhook_processor",
        "app.workers.jira_sync_tasks"
    ]
)

# Celery configuration for high throughput
celery_app.conf.update(
    # Task routing and execution
    task_routes={
        "app.workers.webhook_processor.*": {"queue": "webhook_events"},
        "app.workers.jira_sync_tasks.*": {"queue": "jira_sync"}
    },
    
    # Worker configuration for high throughput
    worker_concurrency=4,  # Number of concurrent worker processes
    worker_prefetch_multiplier=4,  # Tasks to prefetch per worker
    task_acks_late=True,  # Acknowledge tasks after completion
    worker_disable_rate_limits=False,
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Performance optimizations
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_compression="gzip",
    
    # Rate limiting for webhook processing (1000+ events/minute)
    task_annotations={
        "app.workers.webhook_processor.process_webhook_event": {
            "rate_limit": "20/s",  # 1200/minute capacity per worker
            "max_retries": 3,
            "default_retry_delay": 60,
            "retry_backoff": True,
            "retry_jitter": True
        },
        "app.workers.jira_sync_tasks.sync_issue_data": {
            "rate_limit": "10/s",  # API rate limiting compliance
            "max_retries": 5,
            "default_retry_delay": 120
        }
    },
    
    # Queue priorities
    task_default_priority=5,
    worker_hijack_root_logger=False,
    
    # Monitoring and health checks
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat scheduler configuration (for periodic tasks)
    beat_schedule={
        "cleanup-old-webhook-events": {
            "task": "app.workers.webhook_processor.cleanup_old_events",
            "schedule": 3600.0,  # Run every hour
        },
        "process-failed-events": {
            "task": "app.workers.webhook_processor.retry_failed_events",
            "schedule": 900.0,  # Run every 15 minutes
        }
    }
)

logger = logging.getLogger(__name__)
logger.info("Celery application configured for high-throughput webhook processing")