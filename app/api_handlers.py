# This module manages API requests and Portainer integration.
import requests
import os
import logging
from dotenv import load_dotenv

# Logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class APIHandler:
    def __init__(self):
        # Load .env file
        load_dotenv()
        
        self.portainer_url = os.getenv("PORTAINER_URL")
        self.portainer_token = os.getenv("PORTAINER_TOKEN")
        self.gotify_url = os.getenv("GOTIFY_URL")
        self.gotify_token = os.getenv("GOTIFY_TOKEN")
        self.healthcheck_url = os.getenv("HEALTHCHECK_URL")

    def send_gotify_notification(self, title, message, priority=5):
        """Sends notification via Gotify."""
        if not self.gotify_url or not self.gotify_token:
            logger.warning("Gotify URL or Token missing. Notification could not be sent.")
            return False

        try:
            url = f"{self.gotify_url}/message?token={self.gotify_token}"
            payload = {
                "title": title,
                "message": message,
                "priority": priority
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Gotify notification sent: {title}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Gotify notification error: {e}")
            return False

    def send_healthcheck_ping(self, status="success"):
        """Pings the Healthcheck URL."""
        if not self.healthcheck_url:
            return

        try:
            # Simple logic to append /fail to the URL (HC.io standard)
            url = self.healthcheck_url
            if status == "fail":
                url = f"{url}/fail"
            
            requests.get(url, timeout=10)
            logger.info(f"Healthcheck ping sent ({status}).")
        except Exception as e:
            logger.error(f"Healthcheck ping error: {e}")

    def get_portainer_backup(self):
        """Fetches stack/container info via Portainer API (Not for backup, informational)."""
        # Note: Portainer API structure may vary by version. Here we perform a basic connection test.
        if not self.portainer_url or not self.portainer_token:
            logger.warning("Portainer settings missing.")
            return None

        headers = {"X-API-Key": self.portainer_token}
        try:
            # Fetch endpoints list
            url = f"{self.portainer_url}/api/endpoints"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Portainer API error: {e}")
            return None
