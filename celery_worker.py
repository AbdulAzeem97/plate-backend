
from celery_config import celery_app

import plate_tasks  # This ensures the tasks are registered

if __name__ == '__main__':
    celery_app.start()