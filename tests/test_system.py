import pytest
from unittest.mock import patch, MagicMock
import subprocess
from src.utils.system import run_command

class TestSystem:
    @patch('src.network.runner.subprocess.run')
    def test_run_command_success(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "command output"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        result = run_command(["echo", "hello"])
        mock_subprocess_run.assert_called_once_with(
            ["echo", "hello"],
            shell=True, check=True, capture_output=True, text=True,
            encoding='utf-8', timeout=None
        )
        assert result == "command output"

    @patch('src.network.runner.subprocess.run')
    def test_run_command_failure(self, mock_subprocess_run, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error output"
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, cmd="false", stderr="error output")
        mock_subprocess_run.return_value = mock_result

        result = run_command(["false"])
        mock_subprocess_run.assert_called_once_with(
            ["false"],
            shell=True, check=True, capture_output=True, text=True,
            encoding='utf-8', timeout=None
        )
        assert result == "Error: error output"

    @patch('src.network.runner.subprocess.run')
    def test_run_command_suppress_errors(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error output"
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, cmd="false", stderr="error output")
        mock_subprocess_run.return_value = mock_result

        result = run_command(["false"], suppress_errors=True)
        mock_subprocess_run.assert_called_once_with(
            ["false"],
            shell=True, check=True, capture_output=True, text=True,
            encoding='utf-8', timeout=None
        )
        assert result == "Error: Command failed but error was suppressed."
