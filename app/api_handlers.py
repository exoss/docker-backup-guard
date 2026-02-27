# This module manages API requests and Portainer integration.
import requests
import os
import logging
import urllib3
import re
from dotenv import load_dotenv
from app.security import decrypt_value

# Suppress InsecureRequestWarning for local self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging settings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class APIHandler:
    def __init__(self):
        # Load .env file
        env_path = ".env/config.env" if os.path.isdir(".env") else ".env"
        load_dotenv(dotenv_path=env_path)
        
        self.portainer_url = os.getenv("PORTAINER_URL")
        self.portainer_token = decrypt_value(os.getenv("PORTAINER_TOKEN"))
        self.gotify_url = os.getenv("GOTIFY_URL")
        self.gotify_token = decrypt_value(os.getenv("GOTIFY_TOKEN"))
        self.healthcheck_url = os.getenv("HEALTHCHECK_URL")

    def send_gotify_notification(self, title, message, priority=5):
        """Sends notification via Gotify."""
        if not self.gotify_url or not self.gotify_token:
            logger.warning("Gotify URL or Token missing. Notification could not be sent.")
            return False

        try:
            # Fix URL concatenation to avoid double slashes
            base_url = self.gotify_url.rstrip("/")
            url = f"{base_url}/message?token={self.gotify_token}"
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

    def download_portainer_backup(self, output_path, password=None):
        """
        Downloads Portainer configuration backup via API.
        POST /api/backup
        """
        if not self.portainer_url or not self.portainer_token:
            logger.warning("Portainer credentials missing. Cannot perform API backup.")
            return False

        headers = {"X-API-Key": self.portainer_token}
        
        # Ensure URL doesn't end with slash
        base_url = self.portainer_url.rstrip("/")
        url = f"{base_url}/api/backup"
        
        # Payload: Portainer expects a JSON with password if encryption is desired.
        # If password is None/Empty, it might return unencrypted or fail depending on version.
        # We'll use the provided password (usually system backup password) for security.
        payload = {}
            
        try:
            logger.info(f"Requesting Portainer backup from {url}...")
            # verify=False is used because local Portainer often has self-signed certs
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60, verify=False)
            
            # Log status code and headers for debugging
            logger.info(f"Portainer Backup Response Status: {response.status_code}")
            logger.debug(f"Response Headers: {response.headers}")
            try:
                logger.info(f"Content-Disposition: {response.headers.get('Content-Disposition')}")
                logger.info(f"Content-Length: {response.headers.get('Content-Length')}")
            except Exception:
                pass

            response.raise_for_status()
            
            # Check Content-Type to ensure we didn't get a JSON error or HTML page
            content_type = response.headers.get("Content-Type", "").lower()
            logger.info(f"Received Content-Type: {content_type}")

            if "json" in content_type or "text" in content_type:
                # If we can read the response safely, log it
                try:
                    error_msg = response.text[:500]
                except:
                    error_msg = "Could not read response text."
                logger.error(f"Invalid Content-Type received: {content_type}. Response: {error_msg}")
                return None
            
            save_path = output_path
            try:
                if os.path.isdir(output_path):
                    disposition = response.headers.get("Content-Disposition") or ""
                    suggested = None
                    m = re.search(r'filename\\*?=(?:"?)([^";]+)', disposition, flags=re.IGNORECASE)
                    if m:
                        suggested = os.path.basename(m.group(1).strip())
                    if not suggested:
                        if "gzip" in content_type:
                            suggested = "portainer_backup.tar.gz"
                        elif "x-tar" in content_type:
                            suggested = "portainer_backup.tar"
                        else:
                            suggested = "portainer_backup.bin"
                    save_path = os.path.join(output_path, suggested)
            except Exception:
                pass

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(save_path)
            if file_size < 100:
                try:
                    with open(save_path, 'r', errors='ignore') as f:
                        logger.error(f"Downloaded file is too small. Preview: {f.read(200)}")
                except Exception:
                    pass
                return None
                    
            logger.info(f"Portainer backup downloaded successfully: {save_path}")
            return save_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Portainer API Backup error: {e}")
            # Try to log response text if available for debugging
            if hasattr(e, 'response') and e.response:
                logger.error(f"API Response: {e.response.text}")
            return None

    @staticmethod
    def test_portainer_connection(url, token):
        """Tests connectivity to Portainer API using provided credentials."""
        if not url or not token:
            return None

        headers = {"X-API-Key": token}
        try:
            # Ensure URL doesn't end with slash
            base_url = url.rstrip("/")
            # Fetch endpoints list as a test
            api_url = f"{base_url}/api/endpoints"
            # verify=False is used because local Portainer often has self-signed certs
            response = requests.get(api_url, headers=headers, timeout=5, verify=False)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Portainer Connection Test failed: {e}")
            return None

    @staticmethod
    def test_gotify_connection(url, token):
        """Tests connectivity to Gotify API using provided credentials."""
        if not url or not token:
            return False

        try:
            # Fix URL concatenation to avoid double slashes
            base_url = url.rstrip("/")
            # Send a test message
            api_url = f"{base_url}/message?token={token}"
            payload = {
                "title": "Test Notification",
                "message": "This is a test message from Docker Backup Guard.",
                "priority": 5
            }
            response = requests.post(api_url, json=payload, timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Gotify Connection Test failed: {e}")
            return False
