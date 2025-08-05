import pytest
from unittest.mock import patch, mock_open, MagicMock, ANY, call
from src.network.sysctl import (
    get_sysctl_value,
    write_sysctl_config,
    apply_sysctl_from_conf,
    backup_settings,
    revert_settings,
    SYSCTL_CONF_FILE,
    BACKUP_FILE
)
import json

@pytest.fixture
def mock_run_command():
    with patch('src.network.sysctl.run_command') as mock:
        yield mock

class TestSysctl:
    def test_get_sysctl_value_success(self, mock_run_command):
        mock_run_command.return_value = "1"
        value = get_sysctl_value("net.ipv4.ip_forward")
        mock_run_command.assert_called_once_with("sysctl -n net.ipv4.ip_forward", timeout=5)
        assert value == "1"

    def test_get_sysctl_value_not_found(self, mock_run_command):
        mock_run_command.return_value = ""
        value = get_sysctl_value("non.existent.param")
        mock_run_command.assert_called_once_with("sysctl -n non.existent.param", timeout=5)
        assert value == ""

    def test_apply_sysctl_from_conf(self, mock_run_command):
        apply_sysctl_from_conf()
        mock_run_command.assert_called_once_with("sysctl -p /etc/sysctl.d/tcp-optimizer.conf", timeout=5)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=False) # Simulate no existing backup
    @patch('json.dump')
    def test_backup_settings_success(self, mock_json_dump, mock_exists, mock_open_file, mock_run_command):
        mock_run_command.side_effect = ["1", "cubic"]
        
        params_to_backup = ["net.ipv4.ip_forward", "net.ipv4.tcp_congestion_control"]
        result = backup_settings(params_to_backup)
        
        mock_run_command.assert_any_call("sysctl -n net.ipv4.ip_forward", timeout=5)
        mock_run_command.assert_any_call("sysctl -n net.ipv4.tcp_congestion_control", timeout=5)
        mock_open_file.assert_called_once_with(BACKUP_FILE, "w")
        mock_data = {"net.ipv4.ip_forward": "1", "net.ipv4.tcp_congestion_control": "cubic"}
        mock_json_dump.assert_called_once_with(mock_data, ANY, indent=4)
        assert result == "Backup of original settings created."

    @patch("os.path.exists", return_value=True) # Simulate existing backup
    def test_backup_settings_already_exists(self, mock_exists, mock_run_command):
        result = backup_settings([]) # Pass empty list as params_to_backup
        mock_run_command.assert_not_called()
        assert result == "Backup already exists."

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", side_effect=[True, True, True, True])
    @patch('src.network.sysctl.apply_sysctl_from_conf')
    @patch('os.remove')
    def test_revert_settings_success(self, mock_os_remove, mock_apply_sysctl_from_conf, mock_exists, mock_open_file):
        mock_file_content = '{"net.ipv4.ip_forward": "0", "kernel.printk": "4 4 1 7"}'
        mock_open_file.return_value.read.return_value = mock_file_content
        
        result = revert_settings()
        
        expected_calls = [
            call(BACKUP_FILE, "r"),
            call().__enter__(),
            call().read(),
            call().__exit__(None, None, None),
            call().close(),
            call(SYSCTL_CONF_FILE, "w"),
            call().__enter__(),
            call().write('# Linux TCP Optimizer Settings\n'),
            call().write('net.ipv4.ip_forward = 0\n'),
            call().write('kernel.printk = 4 4 1 7\n'),
            call().__exit__(None, None, None),
            call().close()
        ]
        mock_open_file.assert_has_calls(expected_calls)
        mock_apply_sysctl_from_conf.assert_called_once()
        mock_os_remove.assert_any_call(SYSCTL_CONF_FILE)
        mock_os_remove.assert_any_call(BACKUP_FILE)
        assert result == "Settings reverted. All optimizer config and backup files have been deleted."

    @patch("os.path.exists", return_value=False)
    def test_revert_settings_no_backup(self, mock_exists):
        result = revert_settings()
        assert result == "No backup file found. Nothing to revert or delete."

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", side_effect=[True, True])
    @patch('src.network.sysctl.apply_sysctl_from_conf')
    @patch('os.remove')
    def test_revert_settings_corrupted_backup(self, mock_os_remove, mock_apply_sysctl_from_conf, mock_exists, mock_open_file):
        mock_open_file.return_value.read.return_value = '{"net.ipv4.ip_forward": "0", "kernel.printk": "4 4 1 7"'
        
        result = revert_settings()
        
        mock_os_remove.assert_called_once_with(SYSCTL_CONF_FILE)
        assert "Error: Backup file is corrupted. Cannot safely revert." in result