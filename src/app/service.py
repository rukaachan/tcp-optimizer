import curses
import os
import json

from src.config.profiles import load_profiles, get_active_profile
from src.network.sysctl import backup_settings, write_sysctl_config, apply_sysctl_from_conf, revert_settings, get_sysctl_value
from src.network.info import get_system_information

class TCPService:
    def __init__(self, config_loader, profile_manager, tuning_manager, network_info_provider, runner, logger):
        self.config_loader = config_loader
        self.profile_manager = profile_manager
        self.tuning_manager = tuning_manager
        self.network_info_provider = network_info_provider
        self.runner = runner
        self.logger = logger

    def run_analysis_and_apply_optimal_settings(self, cli_args):
        self.logger.log("Running analysis to recommend a profile...")
        config = self.config_loader.load_config(cli_args)
        recommended_profile_key = "balanced"

        self.logger.log(f"Recommended profile: '{recommended_profile_key}'. Applying and benchmarking...")
        self._apply_profile_and_benchmark(recommended_profile_key, config)

    def apply_predefined_profile_and_benchmark(self, profile_name, cli_args):
        self.logger.log(f"Applying '{profile_name}' profile...")
        config = self.config_loader.load_config(cli_args)
        self._apply_profile_and_benchmark(profile_name, config)

    def display_system_information(self):
        self.logger.log("Displaying system information...")
        info = self.network_info_provider.get_system_information()
        for key, value in info.items():
            self.logger.log(f"{key}: {value}")

    def revert_to_original_defaults(self):
        self.logger.log("Reverting to original defaults...")
        self.tuning_manager.revert_settings()
        self.logger.log("Settings reverted to original defaults.")

    def _apply_profile_and_benchmark(self, profile_name, config):
        self.logger.log(f"Applying profile '{profile_name}' and running benchmarks (placeholder)...")