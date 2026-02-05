# This module creates the Streamlit interface.
import streamlit as st
import os
import time
import secrets
import shutil
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
        with col10:
            rclone_remote = st.text_input(get_text(lang, "label_rclone_remote"), value="remote", help=get_text(lang, "help_rclone_remote"))

        st.markdown("---")
        submitted = st.form_submit_button(get_text(lang, "btn_save"), type="primary")

        if submitted:
            # Basic validation
            if not backup_pass:
                st.error(get_text(lang, "error_missing_fields"))
            else:
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
                    "RCLONE_CONFIG_PATH": rclone_path,
                    "RCLONE_REMOTE_NAME": rclone_remote
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
    
    if not candidates:
        st.warning(get_text(lang, "warning_no_candidates"))
    else:
        for container in candidates:
            with st.expander(f"📦 {container.name} ({container.short_id})"):
                st.write(f"**{get_text(lang, 'label_status')}:** {container.status}")
                st.write(f"**{get_text(lang, 'label_image')}:** {container.image.tags}")
                
                # Backup Button
                if st.button(get_text(lang, "btn_backup").format(name=container.name), key=container.id):
                    with st.status(get_text(lang, "status_backing_up").format(name=container.name), expanded=True) as status:
                        st.write(get_text(lang, "status_scanning"))
                        log_placeholder = st.empty()
                        
                        # Start backup process
                        backup_pass = os.getenv("BACKUP_PASSWORD")
                        if not backup_pass:
                            st.error(get_text(lang, "error_no_pass"))
                            status.update(label=get_text(lang, "status_failed"), state="error")
                        else:
                            success = backup_engine.perform_backup(container.id, backup_pass)
                            
                            if success:
                                st.write(get_text(lang, "status_success_encrypt"))
                                st.write(get_text(lang, "status_waiting_cloud"))
                                
                                api = api_handlers.APIHandler()
                                api.send_gotify_notification(
                                    get_text(lang, "notif_success_title"), 
                                    get_text(lang, "notif_success_msg").format(name=container.name)
                                )
                                status.update(label=get_text(lang, "status_complete"), state="complete")
                            else:
                                st.write(get_text(lang, "status_error_process"))
                                api = api_handlers.APIHandler()
                                api.send_gotify_notification(
                                    get_text(lang, "notif_error_title"), 
                                    get_text(lang, "notif_error_msg").format(name=container.name),
                                    priority=8
                                )
                                status.update(label=get_text(lang, "status_error_label"), state="error")

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
