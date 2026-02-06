import schedule
import time
import threading
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from app.engine import BackupEngine

# Configure logging
logger = logging.getLogger("Scheduler")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def run_backup_job():
    """Wrapper to run the backup job."""
    logger.info("⏰ Scheduled backup task started.")
    try:
        engine = BackupEngine()
        engine.perform_backup()
        logger.info("✅ Scheduled backup task completed.")
    except Exception as e:
        logger.error(f"❌ Scheduled backup task failed: {e}")

def scheduler_loop():
    """Main loop for the scheduler thread."""
    logger.info("Scheduler thread started.")
    
    last_config_time = 0
    current_schedule_time = None
    current_enabled = False

    while True:
        try:
            # Reload environment variables to pick up changes from UI
            # We use a specific path to ensure we read the updated file
            env_path = ".env/config.env" if os.path.isdir(".env") else ".env"
            load_dotenv(dotenv_path=env_path, override=True)
            
            enabled = os.getenv("SCHEDULE_ENABLE", "false").lower() == "true"
            backup_time = os.getenv("SCHEDULE_TIME", "03:00")
            
            # Check if config changed
            if enabled != current_enabled or backup_time != current_schedule_time:
                schedule.clear()
                if enabled:
                    schedule.every().day.at(backup_time).do(run_backup_job)
                    logger.info(f"📅 Schedule UPDATED: Runs daily at {backup_time}")
                else:
                    logger.info("⏸️ Schedule DISABLED.")
                
                current_enabled = enabled
                current_schedule_time = backup_time
            
            schedule.run_pending()
            time.sleep(10) # Check every 10 seconds
            
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
            time.sleep(60)

def start_scheduler():
    """Starts the scheduler in a background thread if not already running."""
    # Check if thread is already alive to prevent duplicates
    for t in threading.enumerate():
        if t.name == "BackupSchedulerThread":
            return

    t = threading.Thread(target=scheduler_loop, name="BackupSchedulerThread", daemon=True)
    t.start()
