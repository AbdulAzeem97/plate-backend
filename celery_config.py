from celery import Celery

# Connect to Redis (running locally on port 6379)

celery_app = Celery(
    'plate_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Use gevent pool for better Windows compatibility
celery_app.conf.update(
    #worker_pool='gevent',
    worker_concurrency=4,  # Adjust based on your needs
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Include tasks
celery_app.conf.include = ['plate_tasks']