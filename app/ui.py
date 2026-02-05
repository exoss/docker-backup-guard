# This module creates the Streamlit interface.
import streamlit as st
import os
import time
import secrets
import shutil
import re
from dotenv import load_dotenv
from app import engine
from app import api_handlers
from app.languages import get_text, TRANSLATIONS

ENV_FILE = ".env"

def get_env_path():
    """Determines the correct path for the .env file."""
    # If .env is a directory (Docker mount issue), use a file inside it
    if os.path.isdir(ENV_FILE):
        return os.path.join(ENV_FILE, "config.env")
    return ENV_FILE

def save_env(data):
    """Writes data from the given dictionary to the .env file."""
    try:
        target_file = get_env_path()
        
        with open(target_file, "w") as f:
            for key, value in data.items():
                f.write(f"{key}={value}\n")
            f.flush()
            os.fsync(f.fileno())
        
        # Force reload env to update python environment immediately
        load_dotenv(dotenv_path=target_file, override=True)
        return True
    except Exception as e:
        st.error(f"Error saving settings: {e}")
        return False

def show_setup_wizard():
    """Displays the initial setup wizard."""
    # Language selection for Setup (default to English initially or session state)
    if 'setup_lang' not in st.session_state:
        st.session_state.setup_lang = 'en'

    # Mapping for display names
    lang_options = {"English": "en", "Türkçe": "tr", "Deutsch": "de"}
    
    st.set_page_config(page_title="Restore Container - Setup", page_icon="⚙️", layout="centered")
    
    # Language Selector at the top
    selected_lang_name = st.selectbox(
        "🌍 Language / Dil / Sprache",
        options=list(lang_options.keys()),
        index=0 # Default English
    )
    st.session_state.setup_lang = lang_options[selected_lang_name]
    lang = st.session_state.setup_lang
    
    st.title(get_text(lang, "header_setup"))
    st.markdown("---")
    st.warning(get_text(lang, "warning_env_missing"))
    
    with st.form("setup_form"):
        st.subheader(get_text(lang, "subheader_portainer"))
        st.info(get_text(lang, "info_portainer"))
        col1, col2 = st.columns(2)
        with col1:
            portainer_url = st.text_input(f"{get_text(lang, 'label_portainer_url')} (Optional)", placeholder="http://portainer:9000")
        with col2:
            portainer_token = st.text_input(f"{get_text(lang, 'label_portainer_token')} (Optional)", type="password", help=get_text(lang, 'help_portainer_token'))

        st.markdown("---")
        st.subheader(get_text(lang, "subheader_gotify"))
        st.info(get_text(lang, "info_gotify"))
        col3, col4 = st.columns(2)
        with col3:
            gotify_url = st.text_input(get_text(lang, "label_gotify_url"), placeholder="http://gotify.example.com")
        with col4:
            gotify_token = st.text_input(get_text(lang, "label_gotify_token"), type="password")

        st.markdown("---")
        st.subheader(get_text(lang, "subheader_security"))
        col5, col6 = st.columns(2)
        with col5:
            backup_pass = st.text_input(get_text(lang, "label_backup_pass"), type="password", help=get_text(lang, "help_backup_pass"))
        with col6:
            retention = st.number_input(get_text(lang, "label_retention"), min_value=1, value=7, help=get_text(lang, "help_retention"))
        
        col7, col8 = st.columns(2)
        with col7:
            tz = st.text_input(get_text(lang, "label_timezone"), value="Europe/Berlin")
        with col8:
            healthcheck_url = st.text_input(get_text(lang, "label_healthcheck"), placeholder="https://hc-ping.com/...")

        st.markdown("---")
        st.subheader(get_text(lang, "subheader_rclone"))
        col9, col10 = st.columns(2)
        
        with col9:
            rclone_path = st.text_input(get_text(lang, "label_rclone_path"), value="/app/rclone.conf", help=get_text(lang, "help_rclone_path"))

        # Read existing rclone.conf if available to auto-fill remote name
        existing_conf = ""
        default_remote_name = "remote"
        
        # Check if rclone_path is a directory (Docker mount fix)
        read_path = rclone_path
        if os.path.isdir(rclone_path):
            read_path = os.path.join(rclone_path, "rclone.conf")

        if os.path.exists(read_path) and os.path.isfile(read_path):
            try:
                with open(read_path, "r") as f:
                    existing_conf = f.read()
                
                # Auto-detect remote name from existing config
                match = re.search(r"^\[(.*?)\]", existing_conf, re.MULTILINE)
                if match:
                    default_remote_name = match.group(1)
            except Exception:
                pass

        with col10:
            rclone_remote = st.text_input(get_text(lang, "label_rclone_remote"), value=default_remote_name, help=get_text(lang, "help_rclone_remote"))
            rclone_dest = st.text_input(get_text(lang, "label_rclone_dest"), value="backups", help=get_text(lang, "help_rclone_dest"))

        # Rclone Config Content Editor
        st.markdown(f"""
        **{get_text(lang, 'help_rclone_content_msg')}**  
        👉 [rclone config docs](https://rclone.org/commands/rclone_config/)  
        ℹ️ *{get_text(lang, 'help_rclone_content_hint')}*
        """)

        rclone_content = st.text_area(
            get_text(lang, "label_rclone_content"), 
            value=existing_conf, 
            height=200
        )

        st.markdown("---")
        submitted = st.form_submit_button(get_text(lang, "btn_save"), type="primary")

        if submitted:
            # Basic validation
            if not backup_pass:
                st.error(get_text(lang, "error_missing_fields"))
            else:
                # Handle directory case for rclone_path (common Docker issue)
                real_rclone_path = rclone_path
                if os.path.isdir(rclone_path):
                    real_rclone_path = os.path.join(rclone_path, "rclone.conf")
                    st.warning(get_text(lang, "warning_rclone_isdir").format(path=rclone_path, new_path=real_rclone_path))

                # Save rclone content if provided
                if rclone_content.strip():
                    try:
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(real_rclone_path), exist_ok=True)
                        with open(real_rclone_path, "w") as f:
                            f.write(rclone_content)
                    except Exception as e:
                        st.error(f"Error saving rclone.conf: {e}")

                # Smart Remote Name Detection
                final_remote_name = rclone_remote
                if rclone_content.strip():
                    match = re.search(r"^\[(.*?)\]", rclone_content, re.MULTILINE)
                    if match:
                        detected_name = match.group(1)
                        # Override if user didn't change default "remote" or left it empty
                        if rclone_remote.strip() == "remote" or not rclone_remote.strip():
                            final_remote_name = detected_name

                # Generate random salt for encryption
                random_salt = secrets.token_hex(16)
                
                env_data = {
                    "LANGUAGE": lang,
                    "PORTAINER_URL": portainer_url if portainer_url else "",
                    "PORTAINER_TOKEN": portainer_token if portainer_token else "",
                    "GOTIFY_URL": gotify_url,
                    "GOTIFY_TOKEN": gotify_token,
                    "BACKUP_PASSWORD": backup_pass,
                    "ENCRYPTION_SALT": random_salt,
                    "RETENTION_DAYS": retention,
                    "TZ": tz,
                    "HEALTHCHECK_URL": healthcheck_url,
                    "RCLONE_CONFIG_PATH": real_rclone_path,
                    "RCLONE_REMOTE_NAME": final_remote_name,
                    "RCLONE_DESTINATION": rclone_dest
                }
                
                if save_env(env_data):
                    st.success(get_text(lang, "success_setup"))
                    time.sleep(2)
                    st.rerun()

def show_dashboard():
    """Displays the main control panel."""
    # Load env to get language
    load_dotenv(dotenv_path=get_env_path(), override=True)
    lang = os.getenv("LANGUAGE", "en")
    
    st.set_page_config(page_title=get_text(lang, "page_title_dashboard"), page_icon="📦", layout="wide")
    
    st.sidebar.title(get_text(lang, "menu_title"))
    st.sidebar.success(get_text(lang, "system_online"))
    
    st.title(get_text(lang, "header_dashboard"))
    
    # Start engine
    backup_engine = engine.BackupEngine()
    candidates = backup_engine.get_backup_candidates()
    
    st.subheader(f"{get_text(lang, 'subheader_candidates')} ({len(candidates)})")
    
    # Full Backup Button
    if st.button(get_text(lang, "btn_full_backup"), type="primary", use_container_width=True):
        with st.status(get_text(lang, "status_full_backup_start"), expanded=True) as status:
            # Check password
            backup_pass = os.getenv("BACKUP_PASSWORD")
            if not backup_pass:
                st.error(get_text(lang, "error_no_pass"))
                status.update(label=get_text(lang, "status_failed"), state="error")
            else:
                success = backup_engine.perform_backup()
                
                if success:
                    st.write(get_text(lang, "status_complete"))
                    api = api_handlers.APIHandler()
                    api.send_gotify_notification(
                        get_text(lang, "notif_full_success_title"), 
                        get_text(lang, "notif_full_success_msg")
                    )
                    status.update(label=get_text(lang, "status_complete"), state="complete")
                else:
                    st.write(get_text(lang, "status_error_process"))
                    api = api_handlers.APIHandler()
                    api.send_gotify_notification(
                        get_text(lang, "notif_full_error_title"), 
                        get_text(lang, "notif_full_error_msg"),
                        priority=8
                    )
                    status.update(label=get_text(lang, "status_error_label"), state="error")
    
    if not candidates:
        st.warning(get_text(lang, "warning_no_candidates"))
    else:
        for container in candidates:
            with st.expander(f"📦 {container.name} ({container.short_id})"):
                st.write(f"**{get_text(lang, 'label_status')}:** {container.status}")
                st.write(f"**{get_text(lang, 'label_image')}:** {container.image.tags}")

    st.markdown("---")
    # Show settings
    if st.checkbox(get_text(lang, "checkbox_show_settings")):
        st.code(f"""
        LANGUAGE={os.getenv('LANGUAGE')}
        PORTAINER_URL={os.getenv('PORTAINER_URL')}
        GOTIFY_URL={os.getenv('GOTIFY_URL')}
        RETENTION_DAYS={os.getenv('RETENTION_DAYS')}
        TZ={os.getenv('TZ')}
        RCLONE_REMOTE_NAME={os.getenv('RCLONE_REMOTE_NAME')}
        RCLONE_DESTINATION={os.getenv('RCLONE_DESTINATION')}
        """, language="bash")

def run():
    # Force reload env to get the latest values
    load_dotenv(dotenv_path=get_env_path(), override=True)
    
    # Check if critical configuration exists
    backup_password = os.getenv("BACKUP_PASSWORD")
    
    # If password is missing or empty, show setup
    if not backup_password:
        show_setup_wizard()
    else:
        show_dashboard()
