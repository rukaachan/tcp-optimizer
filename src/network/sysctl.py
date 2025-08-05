import os
import json
from src.utils.system import run_command

SYSCTL_CONF_FILE = "/etc/sysctl.d/tcp-optimizer.conf"
BACKUP_FILE = "/etc/sysctl.d/tcp-optimizer.conf.bak"

def get_sysctl_value(param):
    """Gets the value of a sysctl parameter."""
    return run_command(f"sysctl -n {param}", timeout=5)

def write_sysctl_config(settings):
    """Writes TCP settings to the sysctl config file."""
    with open(SYSCTL_CONF_FILE, "w") as f:
        f.write("\n")
        for key, value in settings.items():
            f.write(f"{key} = {value}\n")

def apply_sysctl_from_conf():
    """Applies settings from the sysctl config file."""
    return run_command(f"sysctl -p {SYSCTL_CONF_FILE}", timeout=5)

def backup_settings(params_to_backup):
    """Backs up current sysctl settings to a file."""
    if os.path.exists(BACKUP_FILE):
        return "Backup already exists."
    current_settings = {}
    for param in params_to_backup:
        try:
            current_settings[param] = get_sysctl_value(param)
        except Exception:
            current_settings[param] = ""
    with open(BACKUP_FILE, "w") as f:
        json.dump(current_settings, f, indent=4)
    return "Backup of original settings created."

def revert_settings():
    """Reverts settings to original values from backup."""
    if not os.path.exists(BACKUP_FILE):
        return "No backup file found. Nothing to revert or delete."

    try:
        with open(BACKUP_FILE, "r") as f:
            settings = json.load(f)
    except json.JSONDecodeError:
        if os.path.exists(SYSCTL_CONF_FILE):
            os.remove(SYSCTL_CONF_FILE)
        return "Error: Backup file is corrupted. Cannot safely revert."

    write_sysctl_config(settings)
    apply_sysctl_from_conf()

    if os.path.exists(SYSCTL_CONF_FILE):
        os.remove(SYSCTL_CONF_FILE)

    if os.path.exists(BACKUP_FILE):
        os.remove(BACKUP_FILE)

    return "Settings reverted. All optimizer config and backup files have been deleted."
