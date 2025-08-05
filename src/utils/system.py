import subprocess

def run_command(cmd, suppress_errors=False):
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True,
            text=True, encoding='utf-8', timeout=None
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        if suppress_errors:
            return "Error: Command failed but error was suppressed."
        return f"Error: {e.stderr}"
