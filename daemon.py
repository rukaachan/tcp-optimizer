#!/usr/bin/env python3

# daemon.py
# The Dynamic Adaptive Tuning Daemon for the Linux TCP Optimizer.

import time
import subprocess
import json
import os
import sys
import logging
from logging.handlers import SysLogHandler
import system_utils as su
import nic_utils as nu

# --- Configuration ---

# File to store the daemon's current status and active profile.
STATUS_FILE = "/tmp/tcp_optimizer_daemon.status"
PROFILES_FILE = "profiles.json" # Location of the profiles and daemon config

# --- Daemon Logic ---

class OptimizerDaemon:
    def __init__(self):
        # Set up logging to the systemd journal
        self.logger = logging.getLogger('TCPOptimizerDaemon')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(SysLogHandler(address='/dev/log'))

        self.config = self.load_config()
        self.profiles = self.config.get("profiles", {})
        self.profile_triggers = self.config.get("daemon_config", {}).get("profile_triggers", {})
        self.check_interval = self.config.get("daemon_config", {}).get("check_interval", 5)
        self.active_nic = nu.get_active_nic()
        self.current_profile_key = "unknown"
        self.pidfile = "/tmp/tcp_optimizer_daemon.pid"

    def get_all_managed_params(self):
        """Collects all unique sysctl parameters managed across all profiles."""
        all_params = set()
        for profile in self.profiles.values():
            for param in profile.get("settings", {}).keys():
                all_params.add(param)
        return list(all_params)

    def load_config(self):
        """Loads the full JSON configuration from the profiles file."""
        try:
            with open(PROFILES_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found at {PROFILES_FILE}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {PROFILES_FILE}: {e}")
            return {}

    def get_running_processes(self):
        """Returns a set of names of all running processes."""
        try:
            output = subprocess.check_output(["ps", "-e", "--no-headers", "-o", "comm"], text=True)
            return set(output.strip().split('\n'))
        except (subprocess.CalledProcessError, FileNotFoundError):
            return set()

    def determine_target_profile(self):
        """Determines which profile should be active based on running processes."""
        running_procs = self.get_running_processes()
        for profile_key, triggers in self.profile_triggers.items():
            for trigger in triggers:
                if any(trigger in proc for proc in running_procs):
                    return profile_key
        return "balanced"  # Default profile if no triggers are met

    def apply_profile(self, profile_key):
        """Applies a specific profile's sysctl and ethtool settings."""
        if not self.profiles or profile_key not in self.profiles:
            self.logger.warning(f"Attempted to apply non-existent profile: {profile_key}")
            return

        profile = self.profiles[profile_key]
        sysctl_settings = profile.get("settings", {})
        ethtool_settings = profile.get("ethtool_settings", {})

        # Apply sysctl settings
        su.write_sysctl_config(sysctl_settings)
        su.apply_sysctl_from_conf()

        # Apply ethtool settings if applicable
        if self.active_nic and ethtool_settings:
            ring_buffer = nu.get_ring_buffer(self.active_nic)
            max_vals = ring_buffer.get('max', {}) if ring_buffer else {}
            rx = max_vals.get('rx') if ethtool_settings.get('rx') == 'max' else ethtool_settings.get('rx')
            tx = max_vals.get('tx') if ethtool_settings.get('tx') == 'max' else ethtool_settings.get('tx')
            if rx and tx: nu.set_ring_buffer(self.active_nic, rx, tx)        
        self.current_profile_key = profile_key
        self.update_status(f"Applied '{profile_key}' profile.")
        self.logger.info(f"Applied '{profile_key}' profile.")

    def update_status(self, message):
        """Writes the current status to the status file."""
        status = {
            "last_update": time.ctime(),
            "active_profile": self.current_profile_key,
            "message": message
        }
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f)

    def run(self):
        """The main loop of the daemon."""
        # Backup original settings on first run
        all_managed_params = self.get_all_managed_params()
        su.backup_settings(all_managed_params)
        if self.active_nic: nu.backup_ethtool_settings(self.active_nic)

        while True:
            target_profile = self.determine_target_profile()
            if target_profile != self.current_profile_key:
                self.apply_profile(target_profile)
            time.sleep(self.check_interval)

    def start(self):
        """Starts the daemon process."""
        if os.path.exists(self.pidfile):
            self.logger.warning("Daemon already running.")
            return
        
        with open(self.pidfile, 'w') as f: f.write(str(os.getpid()))
        self.logger.info("Daemon started.")
        
        try:
            self.run()
        finally:
            os.remove(self.pidfile)
            self.logger.info("Daemon stopped.")

if __name__ == "__main__":
    # This check is for running the script directly, not as a service
    if os.geteuid() != 0:
        print("This script must be run as root.", file=sys.stderr)
        exit(1)
    
    daemon = OptimizerDaemon()
    daemon.start()
