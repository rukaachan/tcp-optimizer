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
    """Executes a shell command and returns its standard output.

    This is a general-purpose wrapper around subprocess.run to simplify
    command execution and capturing output.

    Args:
        command (str): The shell command to execute.
        suppress_errors (bool): If True, returns a generic error message
            instead of raising an exception on command failure.

    Returns:
        str: The stdout from the command, or an error message if it fails.
    """
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if suppress_errors: return f"Error: Command failed but error was suppressed."
        return f"Error: {e.stderr.strip()}"

def get_sysctl_value(param):
    """Retrieves the current value of a single sysctl kernel parameter.

    Args:
        param (str): The name of the sysctl parameter (e.g., 'net.ipv4.tcp_congestion_control').

    Returns:
        str: The current value of the parameter.
    """
    return run_command(f"sysctl -n {param}")

def write_sysctl_config(settings):
    """Writes a dictionary of sysctl settings to the optimizer's config file.

    This function creates or overwrites the configuration file with the specified
    kernel parameters. This file is later applied by `apply_sysctl_from_conf`.

    Args:
        settings (dict): A dictionary where keys are sysctl parameter names and
            values are their desired settings.
    """
    with open(SYSCTL_CONF_FILE, "w") as f:
        f.write("# Linux TCP Optimizer Settings\n")
        for key, value in settings.items(): f.write(f"{key} = {value}\n")

def apply_sysctl_from_conf():
    """Applies kernel parameters using the settings from the optimizer's config file.

    This function uses the `sysctl -p` command to load the values from the
    configuration file into the live kernel.

    Returns:
        str: The output from the `sysctl -p` command.
    """
    return run_command(f"sysctl -p {SYSCTL_CONF_FILE}")

def backup_settings(params_to_backup):
    """Creates a JSON backup of the current values of specified sysctl parameters.

    This function should be run once before any changes are made. It saves the
    original state so it can be restored later with `revert_settings`.

    Args:
        params_to_backup (list): A list of sysctl parameter names to back up.

    Returns:
        str: A message indicating whether the backup was created or already existed.
    """
    if os.path.exists(BACKUP_FILE): return "Backup already exists."
    current_settings = {}
    for param in params_to_backup:
        try: current_settings[param] = get_sysctl_value(param)
        except: current_settings[param] = ""
    with open(BACKUP_FILE, "w") as f: json.dump(current_settings, f, indent=4)
    return "Backup of original settings created."

def revert_settings():
    """Restores sysctl settings from the backup file and cleans up.

    This function reverts the system to its original state by applying the backed-up
    settings. It then removes the optimizer's configuration and backup files.

    Returns:
        str: A status message indicating the result of the revert operation.
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

def read_sysctl_config_file():
    """Reads the optimizer's sysctl configuration file and parses its contents.

    Returns:
        dict: A dictionary of sysctl parameters and their values as found in the
              configuration file, or an empty dictionary if the file is not found
              or cannot be parsed.
    """
    settings = {}
    if not os.path.exists(SYSCTL_CONF_FILE):
        return settings
    try:
        with open(SYSCTL_CONF_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    settings[key.strip()] = value.strip()
    except Exception:
        # Log this error if logging is set up, but for now, just return empty
        pass
    return settings

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
    Identifies the active profile by comparing settings from all known
    profiles against the settings in the optimizer's configuration file.

    Args:
        profiles (dict): A dictionary of all available profiles, typically loaded
                         from `profiles.json`. Each key is a profile name, and
                         its value contains a 'settings' dictionary.

    Returns:
        str: The name of the active profile (e.g., "Balanced", "Gaming") if all its
             settings match the optimizer's configuration file.
             "System Default" if the optimizer's configuration file is not found,
             implying no custom settings are applied by this tool.
             "Unknown (Profiles not loaded)" if the `profiles` argument is empty or None.
             "Custom" if the optimizer's configuration file exists but its settings
             do not perfectly match any known profile.
    """
    # 1. Check if the optimizer's configuration file exists.
    # If not, it implies no settings have been applied by this tool.
    if not os.path.exists(SYSCTL_CONF_FILE):
        return "System Default"

    # 2. Check if profiles data is available.
    if not profiles:
        return "Unknown (Profiles not loaded)"

    # 3. Read the settings currently applied by the optimizer from its config file.
    optimizer_applied_settings = read_sysctl_config_file()

    # 4. Iterate through each known profile and compare its settings with the optimizer's applied settings.
    for profile_key, profile_data in profiles.items():
        profile_settings = profile_data.get('settings')

        # Skip this profile if it's malformed (e.g., no 'settings' dictionary).
        if not profile_settings:
            continue

        is_match = True  # Assume this profile is active until a mismatch is found.

        # Check if all parameters in the profile are present and match in the optimizer's applied settings.
        if len(profile_settings) != len(optimizer_applied_settings):
            is_match = False
        else:
            for param_name, expected_value in profile_settings.items():
                # Normalization (string conversion, stripping whitespace) is crucial for accurate comparison.
                if param_name not in optimizer_applied_settings or \
                   str(optimizer_applied_settings[param_name]).strip() != str(expected_value).strip():
                    is_match = False  # A parameter mismatch means this profile is not active.
                    break  # Exit inner loop; no need to check other params for this profile.

        if is_match:
            # All parameters defined in this profile match the optimizer's applied settings.
            return profile_key.replace('_', ' ').title() # Return formatted profile name.
            
    # 5. If no profile matched all its settings, the configuration is considered "Custom".
    # This means SYSCTL_CONF_FILE exists, but its content doesn't align with any known profile.
    return "Custom"

