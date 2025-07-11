import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import subprocess
from nic_utils import (
    run_command, get_active_nic, get_ring_buffer,
    set_ring_buffer, backup_ethtool_settings, revert_ethtool_settings,
    ETHTOOL_BACKUP_FILE
)

# Mock subprocess.run for run_command tests
@patch('subprocess.run')
def test_run_command_success(mock_run):
    mock_run.return_value = MagicMock(stdout="command output", stderr="", returncode=0)
    assert run_command("echo hello") == "command output"
    mock_run.assert_called_once_with("echo hello", shell=True, check=True, capture_output=True, text=True)

@patch('subprocess.run')
def test_run_command_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error output")
    assert "Error: error output" in run_command("bad command")

# Test get_active_nic
@patch('nic_utils.run_command', side_effect=["eth0", "eth0"]) # First call for primary, second for fallback
def test_get_active_nic_success(mock_run_command):
    assert get_active_nic() == "eth0"
    mock_run_command.assert_called_once() # Only primary command should be called

@patch('nic_utils.run_command', side_effect=["Error: no route", "Error: no route"])
def test_get_active_nic_failure(mock_run_command):
    assert get_active_nic() is None
    assert mock_run_command.call_count == 2 # Both primary and fallback should be called

# Test get_ring_buffer
@patch('nic_utils.run_command')
def test_get_ring_buffer_success(mock_run_command):
    mock_run_command.return_value = (
        "Pre-set maximums:\nRX:             4096\nRX Max:         4096\nTX:             4096\nTX Max:         4096\n" # Simplified output
    )
    result = get_ring_buffer("eth0")
    assert result == {'current': {'rx': 4096, 'tx': 4096}, 'max': {'rx': 4096, 'tx': 4096}}

@patch('nic_utils.run_command', return_value="Error: command failed")
def test_get_ring_buffer_command_failure(mock_run_command):
    assert get_ring_buffer("eth0") is None

def test_get_ring_buffer_no_nic():
    assert get_ring_buffer(None) is None

# Test set_ring_buffer
@patch('nic_utils.run_command', return_value="settings applied")
def test_set_ring_buffer_success(mock_run_command):
    assert set_ring_buffer("eth0", 512, 512) == "settings applied"
    mock_run_command.assert_called_once_with("ethtool -G eth0 rx 512 tx 512")

def test_set_ring_buffer_no_nic():
    assert set_ring_buffer(None, 512, 512) == "Error: No NIC specified."

# Test backup_ethtool_settings
@patch('nic_utils.get_ring_buffer', return_value={'current': {'rx': 256, 'tx': 256}})
@patch('builtins.open', new_callable=mock_open)
def test_backup_ethtool_settings_success(mock_file_open, mock_get_ring_buffer):
    backup_ethtool_settings("eth0")
    mock_file_open.assert_called_once_with(ETHTOOL_BACKUP_FILE, "w")
    handle = mock_file_open()
    handle.write.assert_called_once_with(json.dumps({'rx': 256, 'tx': 256}, indent=4))

def test_backup_ethtool_settings_no_nic():
    # Should not raise an error, just return None
    assert backup_ethtool_settings(None) is None

@patch('nic_utils.get_ring_buffer', return_value=None)
@patch('builtins.open', new_callable=mock_open)
def test_backup_ethtool_settings_no_current_settings(mock_file_open, mock_get_ring_buffer):
    backup_ethtool_settings("eth0")
    mock_file_open.assert_not_called()

# Test revert_ethtool_settings
@patch('builtins.open', new_callable=mock_open, read_data=json.dumps({'rx': 128, 'tx': 128}))
@patch('nic_utils.set_ring_buffer')
def test_revert_ethtool_settings_success(mock_set_ring_buffer, mock_file_open):
    revert_ethtool_settings("eth0")
    mock_file_open.assert_called_once_with(ETHTOOL_BACKUP_FILE, 'r')
    mock_set_ring_buffer.assert_called_once_with("eth0", 128, 128)

@patch('builtins.open', side_effect=FileNotFoundError)
def test_revert_ethtool_settings_no_backup(mock_file_open):
    # Should not raise an error
    revert_ethtool_settings("eth0")
    mock_file_open.assert_called_once_with(ETHTOOL_BACKUP_FILE, 'r')

@patch('builtins.open', new_callable=mock_open, read_data="invalid json")
def test_revert_ethtool_settings_corrupted_backup(mock_file_open):
    # Should not raise an error
    revert_ethtool_settings("eth0")
    mock_file_open.assert_called_once_with(ETHTOOL_BACKUP_FILE, 'r')

def test_revert_ethtool_settings_no_nic():
    # Should not raise an error
    assert revert_ethtool_settings(None) is None
