import pytest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
import subprocess
from system_utils import (
    run_command, get_sysctl_value, write_sysctl_config,
    apply_sysctl_from_conf, backup_settings, revert_settings,
    load_profiles, get_active_profile, read_sysctl_config_file,
    SYSCTL_CONF_FILE, BACKUP_FILE, PROFILES_FILE
)

# Mock subprocess.run for run_command tests
@patch('subprocess.run')
def test_run_command_success(mock_run):
    mock_run.return_value = MagicMock(stdout="success output", stderr="", returncode=0)
    assert run_command("echo hello") == "success output"
    mock_run.assert_called_once_with("echo hello", shell=True, check=True, capture_output=True, text=True)

@patch('subprocess.run')
def test_run_command_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error output")
    assert "Error: error output" in run_command("bad command")

@patch('subprocess.run')
def test_run_command_failure_suppressed(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error output")
    assert "Error: Command failed but error was suppressed." == run_command("bad command", suppress_errors=True)

# Test get_sysctl_value
@patch('system_utils.run_command', return_value="1")
def test_get_sysctl_value(mock_run_command):
    assert get_sysctl_value("net.ipv4.tcp_fastopen") == "1"
    mock_run_command.assert_called_once_with("sysctl -n net.ipv4.tcp_fastopen")

# Test write_sysctl_config
@patch('builtins.open', new_callable=mock_open)
def test_write_sysctl_config(mock_file_open):
    settings = {"net.core.default_qdisc": "fq", "net.ipv4.tcp_congestion_control": "bbr"}
    write_sysctl_config(settings)
    mock_file_open.assert_called_once_with(SYSCTL_CONF_FILE, "w")
    handle = mock_file_open()
    handle.write.assert_any_call("# Linux TCP Optimizer Settings\n")
    handle.write.assert_any_call("net.core.default_qdisc = fq\n")
    handle.write.assert_any_call("net.ipv4.tcp_congestion_control = bbr\n")

# Test apply_sysctl_from_conf
@patch('system_utils.run_command', return_value="applied")
def test_apply_sysctl_from_conf(mock_run_command):
    assert apply_sysctl_from_conf() == "applied"
    mock_run_command.assert_called_once_with(f"sysctl -p {SYSCTL_CONF_FILE}")

# Test backup_settings
@patch('os.path.exists', return_value=False)
@patch('system_utils.get_sysctl_value', side_effect=["1", "bbr"])
@patch('builtins.open', new_callable=mock_open)
def test_backup_settings_new_backup(mock_file_open, mock_get_sysctl_value, mock_exists):
    params = ["param1", "param2"]
    assert backup_settings(params) == "Backup of original settings created."
    mock_exists.assert_called_once_with(BACKUP_FILE)
    mock_get_sysctl_value.assert_any_call("param1")
    mock_get_sysctl_value.assert_any_call("param2")
    mock_file_open.assert_called_once_with(BACKUP_FILE, "w")
    handle = mock_file_open()
    handle.write.assert_called_once_with(json.dumps({"param1": "1", "param2": "bbr"}, indent=4))

@patch('os.path.exists', return_value=True)
def test_backup_settings_backup_exists(mock_exists):
    assert backup_settings([]) == "Backup already exists."
    mock_exists.assert_called_once_with(BACKUP_FILE)

# Test revert_settings
@patch('os.path.exists', side_effect=[True, True, True]) # BACKUP_FILE exists, SYSCTL_CONF_FILE exists, BACKUP_FILE exists
@patch('builtins.open', new_callable=mock_open, read_data=json.dumps({"param1": "old_val"}))
@patch('system_utils.write_sysctl_config')
@patch('system_utils.apply_sysctl_from_conf')
@patch('os.remove')
def test_revert_settings_success(mock_os_remove, mock_apply_sysctl, mock_write_sysctl, mock_file_open, mock_exists):
    assert revert_settings() == "Settings reverted. All optimizer config and backup files have been deleted."
    mock_file_open.assert_called_once_with(BACKUP_FILE, "r")
    mock_write_sysctl.assert_called_once_with({"param1": "old_val"})
    mock_apply_sysctl.assert_called_once()
    mock_os_remove.assert_any_call(SYSCTL_CONF_FILE)
    mock_os_remove.assert_any_call(BACKUP_FILE)

@patch('os.path.exists', return_value=False)
def test_revert_settings_no_backup(mock_exists):
    assert revert_settings() == "No backup file found. Nothing to revert or delete."

@patch('os.path.exists', side_effect=[True, True]) # BACKUP_FILE exists, SYSCTL_CONF_FILE exists
@patch('builtins.open', new_callable=mock_open, read_data="invalid json")
@patch('os.remove')
def test_revert_settings_corrupted_backup(mock_os_remove, mock_file_open, mock_exists):
    assert revert_settings() == "Error: Backup file is corrupted. Cannot safely revert."
    mock_os_remove.assert_called_once_with(SYSCTL_CONF_FILE)

# Test load_profiles
@patch('builtins.open', new_callable=mock_open, read_data=json.dumps({"profile1": {"settings": {}}}))
def test_load_profiles_success(mock_file_open):
    profiles = load_profiles()
    assert profiles is not None and "profile1" in profiles
    mock_file_open.assert_called_once_with(PROFILES_FILE, 'r')

@patch('builtins.open', side_effect=FileNotFoundError)
def test_load_profiles_file_not_found(mock_file_open):
    assert load_profiles() is None

@patch('builtins.open', new_callable=mock_open, read_data="invalid json")
def test_load_profiles_json_decode_error(mock_file_open):
    assert load_profiles() is None

# Test read_sysctl_config_file
@patch('os.path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data="# Comment\nparam1 = value1\nparam2=value2\n")
def test_read_sysctl_config_file_success(mock_open_file, mock_exists):
    settings = read_sysctl_config_file()
    assert settings == {"param1": "value1", "param2": "value2"}
    mock_exists.assert_called_once_with(SYSCTL_CONF_FILE)
    mock_open_file.assert_called_once_with(SYSCTL_CONF_FILE, 'r')

@patch('os.path.exists', return_value=False)
def test_read_sysctl_config_file_not_found(mock_exists):
    settings = read_sysctl_config_file()
    assert settings == {}
    mock_exists.assert_called_once_with(SYSCTL_CONF_FILE)

# Test get_active_profile
@patch('os.path.exists', return_value=True) # SYSCTL_CONF_FILE exists
@patch('system_utils.read_sysctl_config_file', return_value={
    "net.core.default_qdisc": "fq",
    "net.ipv4.tcp_congestion_control": "bbr"
})
def test_get_active_profile_match(mock_read_config_file, mock_exists):
    profiles_data = {
        "balanced": {
            "description": "A solid starting point for most modern broadband connections.",
            "settings": {
                "net.core.default_qdisc": "fq",
                "net.ipv4.tcp_congestion_control": "bbr"
            }
        }
    }
    assert get_active_profile(profiles_data) == "Balanced"
    mock_exists.assert_called_once_with(SYSCTL_CONF_FILE)
    mock_read_config_file.assert_called_once()

@patch('os.path.exists', return_value=False) # SYSCTL_CONF_FILE does not exist
def test_get_active_profile_system_default(mock_exists):
    assert get_active_profile({}) == "System Default"

def test_get_active_profile_no_profiles_loaded():
    assert get_active_profile(None) == "Unknown (Profiles not loaded)"

@patch('os.path.exists', return_value=True) # SYSCTL_CONF_FILE exists
@patch('system_utils.read_sysctl_config_file', return_value={
    "net.core.default_qdisc": "wrong",
    "net.ipv4.tcp_congestion_control": "bbr"
})
def test_get_active_profile_custom(mock_read_config_file, mock_exists):
    profiles_data = {
        "balanced": {
            "description": "A solid starting point for most modern broadband connections.",
            "settings": {
                "net.core.default_qdisc": "fq",
                "net.ipv4.tcp_congestion_control": "bbr"
            }
        }
    }
    assert get_active_profile(profiles_data) == "Custom"

@patch('os.path.exists', return_value=True) # SYSCTL_CONF_FILE exists
@patch('system_utils.read_sysctl_config_file', return_value={
    "net.core.default_qdisc": "fq",
    "net.ipv4.tcp_congestion_control": "bbr",
    "net.ipv4.tcp_something_else": "1"
})
def test_get_active_profile_custom_extra_param(mock_read_config_file, mock_exists):
    profiles_data = {
        "balanced": {
            "description": "A solid starting point for most modern broadband connections.",
            "settings": {
                "net.core.default_qdisc": "fq",
                "net.ipv4.tcp_congestion_control": "bbr"
            }
        }
    }
    assert get_active_profile(profiles_data) == "Custom"
