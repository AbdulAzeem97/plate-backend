# plate_tasks.py
from celery_config import celery_app
from optimizer_logic import greedy_initialize, solve_plate_optimization
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(name='plate_tasks.run_plate_optimization', bind=True)
def run_plate_optimization(self, data):
    try:
        logger.info(f"Starting optimization task for {len(data['tags'])} tags")
        
        tags = data['tags']
        ups_per_plate = data['upsPerPlate']
        plate_count = data['plateCount']
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'status': 'Initializing...'})
        
        seed = greedy_initialize(tags, ups_per_plate, plate_count)
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'status': 'Optimizing...'})
        result = solve_plate_optimization(tags, ups_per_plate, plate_count, seed, verbose=True)
        
        logger.info("Optimization completed successfully")
        return result
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise