import pytest
from unittest.mock import patch, mock_open
from src.config.profiles import load_profiles
import json 

@pytest.fixture
def mock_profiles_json_content():
    return """
    {
        "profile1": {
            "sysctl_settings": {"net.ipv4.ip_forward": 1}
        },
        "profile2": {
            "sysctl_settings": {}
        }
    }
    """

@pytest.fixture
def mock_empty_profiles_json_content():
    return "{}"

class TestProfiles:
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_load_profiles_success(self, mock_json_load, mock_file, mock_profiles_json_content):
        mock_file.return_value.read.return_value = mock_profiles_json_content
        mock_json_load.return_value = {
            "profile1": {
                "sysctl_settings": {"net.ipv4.ip_forward": 1}
            },
            "profile2": {
                "sysctl_settings": {}
            }
        }
        profiles = load_profiles()
        assert "profile1" in profiles
        assert "profile2" in profiles
        assert profiles["profile1"]["sysctl_settings"] == {"net.ipv4.ip_forward": 1}

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load", side_effect=FileNotFoundError)
    def test_load_profiles_file_not_found(self, mock_json_load, mock_file):
        profiles = load_profiles()
        assert profiles is None

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load", side_effect=json.JSONDecodeError("mock error", "doc", 0))
    def test_load_profiles_invalid_json(self, mock_json_load, mock_file):
        profiles = load_profiles()
        assert profiles is None