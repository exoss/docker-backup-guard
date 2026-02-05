# This module contains the backup and restore logic.
import docker
import os
import tarfile
import time
from datetime import datetime
import shutil
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
from rclone_python import rclone

class BackupEngine:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Docker connection error: {e}")
            self.client = None
        
        self.backup_root = "/backups"  # Temporary backup directory
        os.makedirs(self.backup_root, exist_ok=True)
        
        # Load env
        env_path = ".env/config.env" if os.path.isdir(".env") else ".env"
        load_dotenv(dotenv_path=env_path)
        # Updated default path to match docker-compose mount
        self.rclone_config = os.getenv("RCLONE_CONFIG_PATH", "/app/rclone.conf")
        self.rclone_remote_name = os.getenv("RCLONE_REMOTE_NAME", "remote")

    def _log(self, message, level="INFO"):
        """Simple logging function"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        # Gotify integration can be added here in the future

    def _generate_key(self, password):
        """Generates encryption key from password using env salt"""
        salt_hex = os.getenv("ENCRYPTION_SALT")
        
        if not salt_hex:
            self._log("SECURITY WARNING: Using default hardcoded salt!", "WARNING")
            salt = b'restore_container_salt' # Fallback for backward compatibility
        else:
            try:
                salt = bytes.fromhex(salt_hex)
            except ValueError:
                self._log("ERROR: Invalid salt format in .env! Using fallback.", "ERROR")
                salt = b'restore_container_salt'

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _encrypt_file(self, file_path, password):
        """Encrypts the file"""
        key = self._generate_key(password)
        fernet = Fernet(key)
        
        with open(file_path, "rb") as file:
            file_data = file.read()
        
        encrypted_data = fernet.encrypt(file_data)
        
        encrypted_file_path = file_path + ".enc"
        with open(encrypted_file_path, "wb") as file:
            file.write(encrypted_data)
            
        return encrypted_file_path

    def _create_tar_gz(self, source_paths, output_filename):
        """Compresses multiple paths into a single tar.gz file"""
        with tarfile.open(output_filename, "w:gz") as tar:
            for path in source_paths:
                if os.path.exists(path):
                    self._log(f"Archiving: {path}")
                    tar.add(path, arcname=os.path.basename(path))
                else:
                    self._log(f"WARNING: Path not found: {path}", "WARNING")
        return output_filename
    
    def _rclone_sync(self, source_file):
        """Syncs encrypted file to cloud via Rclone (using rclone-python wrapper)"""
        
        if not os.path.exists(self.rclone_config):
            self._log(f"Rclone configuration file not found: {self.rclone_config}", "WARNING")
            return False

        try:
            # Use the configured remote name
            target_path = f"{self.rclone_remote_name}:backups"
            
            self._log(f"Starting Rclone sync: {source_file} -> {target_path}")
            
            # Using rclone-python wrapper
            # We pass the config file path via flags
            rclone.copy(
                source_file, 
                target_path, 
                flags=["--config", self.rclone_config]
            )
            
            self._log("Rclone sync successful.")
            return True
            
        except Exception as e:
            self._log(f"Exception during Rclone operation: {e}", "ERROR")
            return False

    def get_backup_candidates(self):
        """Finds containers to backup (backup.enable=true)"""
        if not self.client:
            return []
        
        candidates = []
        for container in self.client.containers.list():
            labels = container.labels
            if labels.get("backup.enable") == "true":
                candidates.append(container)
        return candidates

    def _resolve_host_path(self, host_path):
        """
        Resolves a host path to the container's mount point.
        If the path starts with /var/lib/docker/volumes, it assumes it's a named volume 
        and is already mounted at the same path.
        Otherwise, it prepends /hostfs to access the host filesystem.
        """
        if host_path.startswith("/var/lib/docker/volumes"):
            return host_path
        
        # Remove leading slash to join correctly
        clean_path = host_path.lstrip("/")
        return os.path.join("/hostfs", clean_path)

    def get_container_volumes(self, container):
        """Finds container volume and bind mount paths (on Host)"""
        mounts = []
        for mount in container.attrs['Mounts']:
            # Bind mounts and Volumes
            if mount['Type'] in ['bind', 'volume']:
                source = mount['Source']
                # Exclude docker socket or system directories if necessary
                if source == "/var/run/docker.sock":
                    continue
                    
                resolved_path = self._resolve_host_path(source)
                mounts.append(resolved_path)
        return mounts

    def perform_backup(self, container_id, backup_password):
        """Executes backup process for a single container"""
        try:
            container = self.client.containers.get(container_id)
            container_name = container.name
            self._log(f"Backup started: {container_name}")

            # 1. Volume/Mount detection
            source_paths = self.get_container_volumes(container)
            
            # CUSTOM_BACKUP_PATH check (Optional, can be taken from container label instead of .env, but let's consider it as a parameter for now)
            # Here we only use the detected ones for simplicity.
            
            if not source_paths:
                self._log(f"No volumes found to backup in container: {container_name}", "WARNING")
                return False

            self._log(f"Detected paths: {source_paths}")

            # 2. Stop container
            self._log(f"Stopping container: {container_name}")
            container.stop()

            try:
                # 3. Compression
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = os.path.join(self.backup_root, f"{container_name}_{timestamp}.tar.gz")
                self._create_tar_gz(source_paths, backup_filename)
                
                # 4. Encryption
                self._log("Encrypting backup...")
                encrypted_file = self._encrypt_file(backup_filename, backup_password)
                
                # Delete original tar.gz (Security/Space saving)
                os.remove(backup_filename)
                
                self._log(f"Backup successfully created: {encrypted_file}")
                
                # 5. Rclone Sync
                self._rclone_sync(encrypted_file)

            except Exception as inner_e:
                self._log(f"Error during backup process: {inner_e}", "ERROR")
                raise inner_e
            finally:
                # 6. Start container (In any case)
                self._log(f"Starting container: {container_name}")
                container.start()

            return True

        except Exception as e:
            self._log(f"Backup failed: {e}", "ERROR")
            return False

if __name__ == "__main__":
    # For testing purposes
    engine = BackupEngine()
    candidates = engine.get_backup_candidates()
    print(f"Candidates: {[c.name for c in candidates]}")
