import time
import schedule
import os
import logging
import requests
import urllib.parse
from dotenv import load_dotenv
from app.engine import BackupEngine

# Configure Logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Scheduler")

def run_backup_job():
    logger.info("⏰ Scheduled Backup Started.")
    # Initialize Engine and Perform Backup
    engine = BackupEngine()
    engine.perform_backup()

def send_heartbeat(url):
    """
    Sends a heartbeat ping to the specified URL.
    This runs independently of the backup job to signal 'System is Alive'.
    """
    try:
        final_url = url
        
        # Uptime Kuma Push Logic
        if "/api/push/" in url:
             try:
                 parsed = urllib.parse.urlparse(url)
                 query = urllib.parse.parse_qs(parsed.query)
                 
                 # Set Status=Up and Msg=Idle
                 query['status'] = ['up']
                 query['msg'] = ['System Idle - Waiting for Schedule']
                 
                 # Update query string
                 new_query = urllib.parse.urlencode(query, doseq=True)
                 final_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
             except Exception:
                 # If parsing fails, use original URL
                 final_url = url

        # Send Request (GET)
        # We use a short timeout (10s) to not block the scheduler for too long
        try:
             requests.get(final_url, timeout=10)
        except requests.exceptions.SSLError:
             # Retry with verify=False for self-hosted instances
             requests.get(final_url, timeout=10, verify=False)
             
    except Exception as e:
        logger.warning(f"Heartbeat failed: {e}")

def scheduler_loop():
    logger.info("Scheduler Service Started.")
    
    # State tracking to detect config changes
    current_schedule_enabled = False
    current_schedule_time = ""
    current_heartbeat_interval = 0
    current_heartbeat_url = ""
    
    # Initial load delay
    time.sleep(2)
    
    while True:
        try:
            # 1. Reload Configuration
            # Handle Docker volume mount edge case where .env might be a dir
            env_path = ".env/config.env" if os.path.isdir(".env") else ".env"
            load_dotenv(dotenv_path=env_path, override=True)
            
            # 2. Read Backup Settings
            enabled = os.getenv("SCHEDULE_ENABLE", "false").lower() == "true"
            backup_time = os.getenv("SCHEDULE_TIME", "03:00")
            
            # 3. Read Heartbeat Settings
            hb_url = os.getenv("HEARTBEAT_URL", "").strip()
            try:
                hb_interval = int(os.getenv("HEARTBEAT_INTERVAL", "0"))
            except ValueError:
                hb_interval = 0
            
            # 4. Check for Changes
            config_changed = (
                enabled != current_schedule_enabled or 
                backup_time != current_schedule_time or
                hb_url != current_heartbeat_url or
                hb_interval != current_heartbeat_interval
            )
            
            if config_changed:
                logger.info("🔄 Configuration changed. Updating scheduler...")
                schedule.clear()
                
                # --- Setup Backup Job ---
                if enabled:
                    schedule.every().day.at(backup_time).do(run_backup_job)
                    logger.info(f"📅 Backup Scheduled for {backup_time}")
                else:
                    logger.info("⏸️ Backup Schedule Disabled.")
                
                # --- Setup Heartbeat Job ---
                if hb_url and hb_interval > 0:
                    schedule.every(hb_interval).minutes.do(send_heartbeat, url=hb_url)
                    logger.info(f"💓 Heartbeat Enabled: Every {hb_interval} minutes -> {hb_url}")
                else:
                    if hb_url:
                        logger.info("💓 Heartbeat Disabled (Interval is 0).")
                    else:
                        logger.info("💓 Heartbeat Disabled (No URL).")

                # Update State
                current_schedule_enabled = enabled
                current_schedule_time = backup_time
                current_heartbeat_url = hb_url
                current_heartbeat_interval = hb_interval

            # 5. Run Pending Jobs
            schedule.run_pending()
            
            # Sleep to prevent high CPU usage
            time.sleep(10)
            
        except Exception as e:
            logger.error(f"Scheduler Loop Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    scheduler_loop()
