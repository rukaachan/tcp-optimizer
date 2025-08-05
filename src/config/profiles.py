import json
import os
from src.network.sysctl import get_sysctl_value

PROFILES_FILE = "profiles.json"
SYSCTL_CONF_FILE = "/etc/sysctl.d/tcp-optimizer.conf"

def load_profiles():
    """Loads TCP profiles from a JSON file."""
    try:
        with open(PROFILES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def get_active_profile(profiles):
    """Identifies the active profile based on current settings."""
    if not os.path.exists(SYSCTL_CONF_FILE):
        return "System Default"
    
    try:
        current_congestion = get_sysctl_value("net.ipv4.tcp_congestion_control")
        current_low_latency = get_sysctl_value("net.ipv4.tcp_low_latency")
        current_wmem_max = get_sysctl_value("net.core.wmem_max")
    except Exception:
        return "Unknown"

    if not profiles:
        return "Unknown (Profiles not loaded)"

    for key, profile_data in profiles.items():
        settings = profile_data['settings']
        if (settings.get("net.ipv4.tcp_congestion_control") == current_congestion and
            settings.get("net.ipv4.tcp_low_latency") == current_low_latency and
            settings.get("net.core.wmem_max") == current_wmem_max):
            return key.replace('_', ' ').title()
            
    return "Custom"