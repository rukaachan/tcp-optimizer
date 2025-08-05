import subprocess
from typing import Tuple

class CommandRunner:
    def run_command(self, command: str, suppress_errors: bool = False, timeout: int | None = None) -> str:
        """
        Runs a shell command and returns its stdout.
        If suppress_errors is True, stderr is not returned on error.
        Optionally, a timeout in seconds can be provided for the command.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=timeout
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if not suppress_errors:
                return f"Error: {e.stderr.strip()}"
            return ""
        except FileNotFoundError:
            if not suppress_errors:
                return f"Error: Command not found: {command.split()[0]}"
            return ""