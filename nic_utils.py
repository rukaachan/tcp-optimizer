# nic_utils.py
# Utility module for Network Interface Card (NIC) operations using ethtool.

import re
import subprocess
import json

# --- Configuration Paths ---
ETHTOOL_BACKUP_FILE = "/etc/sysctl.d/tcp-optimizer.ethtool.bak"

def run_command(command):
    """Executes a shell command and returns its stripped standard output.

    Args:
        command (str): The shell command to execute.

    Returns:
        str: The stdout from the command, or an error message if it fails.
    """
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"

def get_active_nic():
    """Identifies the active primary network interface card (NIC).

    It determines the NIC used for the default route, which is the interface
    handling the majority of internet traffic.

    Returns:
        str: The name of the active NIC (e.g., "eth0"), or None if it cannot be determined.
    """
    command = "ip -o -4 route show to default | awk '{print $5}'"
    nic = run_command(command)
    if "Error:" in nic or not nic:
        # Fallback for systems where the above command fails
        command = "ip route get 8.8.8.8 | awk '{print $5; exit}'"
        nic = run_command(command)
    return nic if "Error:" not in nic and nic else None

def get_ring_buffer(nic):
    """Retrieves the current and maximum RX/TX ring buffer sizes for a given NIC.

    Uses `ethtool -g` to query the hardware settings.

    Args:
        nic (str): The name of the network interface (e.g., "eth0").

    Returns:
        dict: A dictionary containing the current and maximum buffer sizes,
              e.g., {'current': {'rx': 256, 'tx': 256}, 'max': {'rx': 4096, 'tx': 4096}},
              or None if the command fails.
    """
    if not nic: return None
    output = run_command(f"ethtool -g {nic}")
    if "Error:" in output: return None
    
    settings = {'current': {}, 'max': {}}
    try:
        for line in output.split('\n'):
            if line.startswith("RX:"):
                settings['current']['rx'] = int(line.split()[-1])
            elif line.startswith("TX:"):
                settings['current']['tx'] = int(line.split()[-1])
            elif line.startswith("RX Max:"):
                settings['max']['rx'] = int(line.split()[-1])
            elif line.startswith("TX Max:"):
                settings['max']['tx'] = int(line.split()[-1])
    except (IndexError, ValueError):
        return None
    return settings

def set_ring_buffer(nic, rx, tx):
    """Sets the RX and TX ring buffer sizes for a given NIC.

    Uses `ethtool -G` to apply the settings.

    Args:
        nic (str): The name of the network interface (e.g., "eth0").
        rx (int): The desired RX ring buffer size.
        tx (int): The desired TX ring buffer size.

    Returns:
        str: The output from the `ethtool` command.
    """
    if not nic: return "Error: No NIC specified."
    return run_command(f"ethtool -G {nic} rx {rx} tx {tx}")

def backup_ethtool_settings(nic):
    """Creates a JSON backup of the current ring buffer settings for a NIC.

    Args:
        nic (str): The name of the network interface.
    """
    if not nic: return
    current_settings = get_ring_buffer(nic)
    if current_settings:
        with open(ETHTOOL_BACKUP_FILE, "w") as f:
            json.dump(current_settings['current'], f, indent=4)

def revert_ethtool_settings(nic):
    """Restores the ring buffer settings for a NIC from the backup file.

    If the backup file doesn't exist or is invalid, it does nothing.

    Args:
        nic (str): The name of the network interface.
    """
    if not nic: return
    try:
        with open(ETHTOOL_BACKUP_FILE, 'r') as f:
            backup = json.load(f)
        rx = backup.get('rx')
        tx = backup.get('tx')
        if rx and tx:
            set_ring_buffer(nic, rx, tx)
    except (FileNotFoundError, json.JSONDecodeError):
        pass # No backup or corrupted, nothing to do
