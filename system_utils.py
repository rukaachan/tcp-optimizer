# system_utils.py
# Utility module for TCP optimization operations on Linux.

import subprocess
import os
import json

# --- Configuration Paths ---
SYSCTL_CONF_FILE = "/etc/sysctl.d/tcp-optimizer.conf"
BACKUP_FILE = "/etc/sysctl.d/tcp-optimizer.conf.bak"
PROFILES_FILE = "profiles.json"

# --- Core System Functions ---

def run_command(command, suppress_errors=False):
    """Runs a shell command and returns its output."""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if suppress_errors: return f"Error: Command failed but error was suppressed."
        return f"Error: {e.stderr.strip()}"

def get_sysctl_value(param):
    """Gets the value of a sysctl parameter."""
    return run_command(f"sysctl -n {param}")

def write_sysctl_config(settings):
    """Writes TCP settings to the sysctl config file."""
    with open(SYSCTL_CONF_FILE, "w") as f:
        f.write("# Linux TCP Optimizer Settings\n")
        for key, value in settings.items(): f.write(f"{key} = {value}\n")

def apply_sysctl_from_conf():
    """Applies settings from the sysctl config file."""
    return run_command(f"sysctl -p {SYSCTL_CONF_FILE}")

def backup_settings(params_to_backup):
    """Backs up current sysctl settings to a file."""
    if os.path.exists(BACKUP_FILE): return "Backup already exists."
    current_settings = {}
    for param in params_to_backup:
        try: current_settings[param] = get_sysctl_value(param)
        except: current_settings[param] = ""
    with open(BACKUP_FILE, "w") as f: json.dump(current_settings, f, indent=4)
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

# --- Profile Management Functions ---

def load_profiles():
    """Loads TCP profiles from a JSON file."""
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
    Identifies the active profile by comprehensively comparing settings from all known
    profiles against the current system's sysctl values.

    Args:
        profiles (dict): A dictionary of all available profiles, typically loaded
                         from `profiles.json`. Each key is a profile name, and
                         its value contains a 'settings' dictionary.

    Returns:
        str: The name of the active profile (e.g., "Balanced", "Gaming") if all its
             settings match the current system values.
             "System Default" if the optimizer's configuration file is not found,
             implying no custom settings are applied.
             "Unknown (Profiles not loaded)" if the `profiles` argument is empty or None.
             "Custom" if the current system settings do not perfectly match all
             parameters of any known profile, but a custom config file exists.
             This indicates user modifications or a partially applied profile.
    """
    # 1. Check if the optimizer's configuration file exists.
    # If not, it implies no settings have been applied by this tool.
    if not os.path.exists(SYSCTL_CONF_FILE):
        return "System Default"

    # 2. Check if profiles data is available.
    if not profiles:
        return "Unknown (Profiles not loaded)"

    # 3. Iterate through each known profile and compare its settings with live system values.
    for profile_key, profile_data in profiles.items():
        profile_settings = profile_data.get('settings')

        # Skip this profile if it's malformed (e.g., no 'settings' dictionary).
        if not profile_settings:
            continue

        is_match = True  # Assume this profile is active until a mismatch is found.
        # For the current profile, check each of its defined parameters.
        for param_name, expected_value in profile_settings.items():
            try:
                current_value = get_sysctl_value(param_name)
                # Compare current system value with the profile's expected value.
                # Normalization (string conversion, stripping whitespace) is crucial for accurate comparison.
                if str(current_value).strip() != str(expected_value).strip():
                    is_match = False  # A parameter mismatch means this profile is not active.
                    break  # Exit inner loop; no need to check other params for this profile.
            except Exception:
                # If reading a sysctl value fails (e.g., parameter unsupported on the system),
                # this profile cannot be considered a match.
                is_match = False
                break  # Exit inner loop.

        if is_match:
            # All parameters defined in this profile match the current system settings.
            return profile_key.replace('_', ' ').title() # Return formatted profile name.
            
    # 4. If no profile matched all its settings, the configuration is considered "Custom".
    # This means SYSCTL_CONF_FILE exists, but its content doesn't align with any known profile.
    return "Custom"
