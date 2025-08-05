import os
import json
from typing import Dict, Any, List

class NetworkTuningManager:
    def __init__(self, runner, logger):
        self.runner = runner
        self.logger = logger
        self.sysctl_conf_file = "/etc/sysctl.d/tcp-optimizer.conf"
        self.backup_file = "/etc/sysctl.d/tcp-optimizer.conf.bak"

    def apply_settings(self, settings: Dict[str, str]):
        """Applies sysctl settings from a given dictionary."""
        self.logger.log("Applying sysctl settings...")
        config_lines = [f"{key}={value}" for key, value in settings.items()]
        self._write_sysctl_config(config_lines)
        self._apply_sysctl_from_conf()
        self.logger.log("Sysctl settings applied.")

    def revert_settings(self):
        """Reverts settings to original state from backup."""
        self.logger.log("Reverting settings to original defaults...")
        if not os.path.exists(self.backup_file):
            self.logger.log("No backup file found. Cannot revert.")
            return "No backup file found. Cannot revert."
        
        try:
            with open(self.backup_file, 'r') as f:
                backup_settings = json.load(f)
            self._write_sysctl_config([f"{key}={value}" for key, value in backup_settings.items()])
            self._apply_sysctl_from_conf()
            os.remove(self.backup_file)
            self.logger.log("Settings reverted from backup.")
            return "Settings reverted to original defaults from backup."
        except json.JSONDecodeError:
            self.logger.log("Error: The backup file is corrupted. Cannot revert.")
            return "Error: The backup file is corrupted. Cannot revert."
        except Exception as e:
            self.logger.log(f"Error during revert: {e}")
            return f"Error during revert: {e}"

    def backup_settings(self, params_to_backup: List[str]):
        """Backs up current sysctl settings for specified parameters."""
        self.logger.log("Backing up current sysctl settings...")
        current_settings = {}
        for param in params_to_backup:
            value = self._get_sysctl_value(param)
            if value is not None:
                current_settings[param] = value
        
        with open(self.backup_file, 'w') as f:
            json.dump(current_settings, f, indent=2)
        self.logger.log("Current settings backed up.")

    def _write_sysctl_config(self, config_lines: List[str]):
        """Writes sysctl configuration to a file."""
        with open(self.sysctl_conf_file, 'w') as f:
            for line in config_lines:
                f.write(line + "\n")

    def _apply_sysctl_from_conf(self):
        """Applies sysctl settings from the configuration file."""
        self.runner.run_command(f"sudo sysctl --system")

    def _get_sysctl_value(self, param: str) -> Optional[str]:
        """Gets the current value of a sysctl parameter."""
        result = self.runner.run_command(f"sysctl -n {param}", suppress_errors=True)
        if result and "Error" not in result:
            return result.strip()
        return None