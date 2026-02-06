# This module creates the Streamlit interface.
import streamlit as st
import os
import time
import json
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
    """Displays the main control panel with tabs."""
    # Load env to get language
    load_dotenv(dotenv_path=get_env_path(), override=True)
    lang = os.getenv("LANGUAGE", "en")
    
    st.set_page_config(page_title=get_text(lang, "page_title_dashboard"), page_icon="📦", layout="wide")
    
    st.sidebar.title(get_text(lang, "menu_title"))
    st.sidebar.success(get_text(lang, "system_online"))
    
    st.title(get_text(lang, "header_dashboard"))
    
    # Initialize Engine
    backup_engine = engine.BackupEngine()

    # Create Tabs
    tab_dash, tab_settings, tab_actions, tab_logs = st.tabs([
        "📊 " + get_text(lang, "tab_dashboard"), 
        "⚙️ " + get_text(lang, "tab_settings"), 
        "🚀 " + get_text(lang, "tab_actions"), 
        "📜 " + get_text(lang, "tab_logs")
    ])

    # --- TAB 1: DASHBOARD ---
    with tab_dash:
        st.header(get_text(lang, "header_overview"))
        
        # Load State
        state_path = "/backups/backup_state.json"
        state = {}
        if os.path.exists(state_path):
            try:
                with open(state_path, "r") as f:
                    state = json.load(f)
            except:
                pass
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(get_text(lang, "metric_last_success"), state.get("last_success", "Never"))
        with col2:
            size_mb = state.get("last_size_bytes", 0) / (1024*1024)
            st.metric(get_text(lang, "metric_last_size"), f"{size_mb:.2f} MB")
        with col3:
            st.metric(get_text(lang, "metric_protected"), state.get("protected_containers", 0))

        st.markdown("---")
        
        # Quick Action: Full Backup
        if st.button(get_text(lang, "btn_full_backup"), type="primary", use_container_width=True):
            with st.status(get_text(lang, "status_full_backup_start"), expanded=True) as status:
                if not os.getenv("BACKUP_PASSWORD"):
                    st.error(get_text(lang, "error_no_pass"))
                    status.update(label=get_text(lang, "status_failed"), state="error")
                else:
                    success = backup_engine.perform_backup()
                    if success:
                        st.success(get_text(lang, "status_complete"))
                        api_handlers.APIHandler().send_gotify_notification(
                            get_text(lang, "notif_full_success_title"), 
                            get_text(lang, "notif_full_success_msg")
                        )
                        status.update(label=get_text(lang, "status_complete"), state="complete")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(get_text(lang, "status_error_process"))
                        api_handlers.APIHandler().send_gotify_notification(
                            get_text(lang, "notif_full_error_title"), 
                            get_text(lang, "notif_full_error_msg"), priority=8
                        )
                        status.update(label=get_text(lang, "status_error_label"), state="error")

    # --- TAB 2: SETTINGS ---
    with tab_settings:
        st.header(get_text(lang, "header_config"))
        
        # Edit Mode Toggle
        if 'settings_edit_mode' not in st.session_state:
            st.session_state.settings_edit_mode = False
            
        def toggle_edit():
            st.session_state.settings_edit_mode = not st.session_state.settings_edit_mode
            
        st.toggle(get_text(lang, "toggle_edit"), value=st.session_state.settings_edit_mode, on_change=toggle_edit)
        
        disabled = not st.session_state.settings_edit_mode
        
        with st.form("settings_editor"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                new_portainer_url = st.text_input("Portainer URL", value=os.getenv("PORTAINER_URL", ""), disabled=disabled)
                new_gotify_url = st.text_input("Gotify URL", value=os.getenv("GOTIFY_URL", ""), disabled=disabled)
                new_retention = st.number_input("Retention (Days)", value=int(os.getenv("RETENTION_DAYS", "7")), min_value=1, disabled=disabled)
            with col_s2:
                new_portainer_token = st.text_input("Portainer Token", value=os.getenv("PORTAINER_TOKEN", ""), type="password", disabled=disabled)
                new_gotify_token = st.text_input("Gotify Token", value=os.getenv("GOTIFY_TOKEN", ""), type="password", disabled=disabled)
                new_tz = st.text_input("Timezone", value=os.getenv("TZ", "Europe/Berlin"), disabled=disabled)
                
            submitted = st.form_submit_button(get_text(lang, "btn_save_changes"), disabled=disabled)
            
            if submitted:
                env_updates = {
                    "PORTAINER_URL": new_portainer_url,
                    "PORTAINER_TOKEN": new_portainer_token,
                    "GOTIFY_URL": new_gotify_url,
                    "GOTIFY_TOKEN": new_gotify_token,
                    "RETENTION_DAYS": new_retention,
                    "TZ": new_tz
                }
                if save_env(env_updates):
                    st.success("Settings saved! Reloading...")
                    st.session_state.settings_edit_mode = False
                    time.sleep(1)
                    st.rerun()

    # --- TAB 3: ACTION CENTER ---
    with tab_actions:
        candidates = backup_engine.get_backup_candidates()
        st.subheader(f"{get_text(lang, 'subheader_candidates')} ({len(candidates)})")
        
        if not candidates:
            st.warning(get_text(lang, "warning_no_candidates"))
        else:
            for container in candidates:
                with st.expander(f"📦 {container.name} ({container.short_id})"):
                    st.write(f"**{get_text(lang, 'label_status')}:** {container.status}")
                    st.write(f"**{get_text(lang, 'label_image')}:** {container.image.tags}")
                    
                    if st.button(get_text(lang, "btn_backup").format(name=container.name), key=f"btn_{container.id}"):
                        with st.status(get_text(lang, "status_backing_up").format(name=container.name), expanded=True) as status:
                            if not os.getenv("BACKUP_PASSWORD"):
                                 st.error(get_text(lang, "error_no_pass"))
                                 status.update(label=get_text(lang, "status_failed"), state="error")
                            else:
                                success = backup_engine.perform_backup(container_id=container.id)
                                if success:
                                    st.success(get_text(lang, "status_complete"))
                                    api_handlers.APIHandler().send_gotify_notification(
                                        get_text(lang, "notif_success_title"), 
                                        get_text(lang, "notif_success_msg").format(name=container.name)
                                    )
                                    status.update(label=get_text(lang, "status_complete"), state="complete")
                                else:
                                    st.error(get_text(lang, "status_error_process"))
                                    api_handlers.APIHandler().send_gotify_notification(
                                        get_text(lang, "notif_error_title"), 
                                        get_text(lang, "notif_error_msg").format(name=container.name), priority=8
                                    )
                                    status.update(label=get_text(lang, "status_error_label"), state="error")

    # --- TAB 4: LOGS ---
    with tab_logs:
        st.header(get_text(lang, "header_logs"))
        if st.button(get_text(lang, "btn_refresh_logs")):
            st.rerun()
            
        log_path = "logs/app.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                # Read last 200 lines
                lines = f.readlines()[-200:]
                log_content = "".join(lines)
            st.code(log_content, language="log")
        else:
            st.info("No logs found.")

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
