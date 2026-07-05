import time
import schedule
import os
import logging
import requests
import urllib.parse
import urllib3
import warnings
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

_heartbeat_session = requests.Session()

def run_backup_job():
    logger.info("⏰ Scheduled Backup Started.")
    # Initialize Engine and Perform Backup
    engine = BackupEngine()
    engine.perform_backup()

def _prepare_heartbeat_url(url):
    """Pre-calculate the final heartbeat URL with status/msg query parameters.

    Extracted from the hot send_heartbeat loop so URL parsing is done once
    during config load, not on every periodic tick.
    """
    if not url:
        return ""
    if "/api/push/" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            query['status'] = ['up']
            query['msg'] = ['System Idle - Waiting for Schedule']
            new_query = urllib.parse.urlencode(query, doseq=True)
            return urllib.parse.urlunparse(parsed._replace(query=new_query))
        except Exception:
            return url
    return url

def send_heartbeat(url):
    """
    Sends a heartbeat ping to the specified URL.
    URL is pre-calculated by _prepare_heartbeat_url during config load.
    This runs independently of the backup job to signal 'System is Alive'.
    """
    try:
        # Send Request (GET)
        # verify=False: heartbeat URLs are typically self-hosted (Uptime Kuma) with self-signed certs
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
            _heartbeat_session.get(url, timeout=10, verify=False)
    except Exception as e:
        logger.warning(f"Heartbeat failed: {e}")

def scheduler_loop():
    logger.info("Scheduler Service Started.")
    
    # State tracking to detect config changes
    current_schedule_enabled = False
    current_schedule_time = ""
    current_heartbeat_interval = 0
    current_heartbeat_url = ""
    last_env_mtime = 0
    
    # Initial load delay
    time.sleep(2)
    
    while True:
        try:
            # 1. Reload Configuration
            # Handle Docker volume mount edge case where .env might be a dir
            env_path = ".env/config.env" if os.path.isdir(".env") else ".env"

            # Check modification time to avoid redundant reloads
            try:
                mtime = os.stat(env_path).st_mtime
            except FileNotFoundError:
                mtime = 0

            if mtime != last_env_mtime:
                load_dotenv(dotenv_path=env_path, override=True)
                last_env_mtime = mtime
            
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
                    prepared_url = _prepare_heartbeat_url(hb_url)
                    schedule.every(hb_interval).minutes.do(send_heartbeat, url=prepared_url)
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
