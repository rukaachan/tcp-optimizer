# system_utils.py
# Utility module for system operations related to TCP optimization on Linux systems.

import subprocess
import os
import json

# --- Configuration Paths ---
# Define file paths for system configuration and backup files used in TCP optimization.
SYSCTL_CONF_FILE = "/etc/sysctl.d/99-arch-tcp-optimizer.conf"
BACKUP_FILE = "/etc/sysctl.d/99-arch-tcp-optimizer.conf.bak"
PROFILES_FILE = "profiles.json"

# --- Core System Functions ---

def run_command(command, suppress_errors=False):
    """
    Executes a shell command and returns its output as a string.
    Optionally suppresses error messages if the command fails.
    """
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if suppress_errors: return f"Error: Command failed but error was suppressed."
        return f"Error: {e.stderr.strip()}"

def get_sysctl_value(param):
    """Retrieves the current value of a specified sysctl parameter."""
    return run_command(f"sysctl -n {param}")

def write_sysctl_config(settings):
    """
    Writes a dictionary of TCP settings to the sysctl configuration file.
    Overwrites the file with the provided settings, adding a header comment.
    """
    with open(SYSCTL_CONF_FILE, "w") as f:
        f.write("# Arch TCP Optimizer Settings\n")
        for key, value in settings.items(): f.write(f"{key} = {value}\n")

def apply_sysctl_from_conf():
    """Applies the settings from the sysctl configuration file to the system."""
    return run_command(f"sysctl -p {SYSCTL_CONF_FILE}")

def backup_settings(params_to_backup):
    """
    Creates a backup of the current sysctl settings for specified parameters.
    Saves the backup to a predefined file path if it doesn't already exist.
    """
    if os.path.exists(BACKUP_FILE): return "Backup already exists."
    current_settings = {}
    for param in params_to_backup:
        try: current_settings[param] = get_sysctl_value(param)
        except: current_settings[param] = ""
    with open(BACKUP_FILE, "w") as f: json.dump(current_settings, f, indent=4)
    return "Backup of original settings created."

def revert_settings():
    """
    Reverts system settings to their original values using a backup file.
    Deletes configuration and backup files after successful reversion.
    """
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

# --- Profile Management Functions ---

def load_profiles():
    """
    Loads TCP optimization profiles from an external JSON file.
    Returns None if the file is not found or corrupted.
    """
    try:
        with open(PROFILES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

# --- Active Profile Detection ---
def get_active_profile(profiles):
    """
    Determines the currently active profile by comparing system settings with loaded profiles.
    Checks key TCP parameters to identify a matching profile, returning a formatted name or status.
    """
    if not os.path.exists(SYSCTL_CONF_FILE):
        return "System Default"
    
    try:
        # Get the three key values that help differentiate profiles
        current_congestion = get_sysctl_value("net.ipv4.tcp_congestion_control")
        current_low_latency = get_sysctl_value("net.ipv4.tcp_low_latency")
        current_wmem_max = get_sysctl_value("net.core.wmem_max")
    except:
        return "Unknown"

    if not profiles: return "Unknown (Profiles not loaded)"

    for key, profile_data in profiles.items():
        settings = profile_data['settings']
        if (settings.get("net.ipv4.tcp_congestion_control") == current_congestion and
            settings.get("net.ipv4.tcp_low_latency") == current_low_latency and
            settings.get("net.core.wmem_max") == current_wmem_max):
            return key.replace('_', ' ').title()
            
    return "Custom"
