from pathlib import Path
from typing import Any, Dict, Optional
import json

class ConfigLoader:
    def __init__(self, profiles_file: str = "profiles.json"):
        self.profiles_file = Path(profiles_file)

    def load_config(self, cli_args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Loads and merges configuration from various sources.
        Precedence: profiles.json < environment variables < CLI overrides.
        """
        config: Dict[str, Any] = {}

        # 1. Load from profiles.json
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r') as f:
                    config.update(json.load(f))
            except json.JSONDecodeError:
                raise ValueError(f"Error: '{self.profiles_file}' is corrupted or invalid JSON.")
        else:
            raise FileNotFoundError(f"Error: '{self.profiles_file}' not found.")


        if cli_args:
            config.update(cli_args)

        return config