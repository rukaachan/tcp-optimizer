import pytest
from unittest.mock import patch, MagicMock
import curses
from src.main import main

class TestMain:
    @pytest.fixture(autouse=True)
    def mock_load_profiles_autouse(self, monkeypatch):
        mock_load_profiles = MagicMock(return_value={"test_profile": {"settings": {}}})
        monkeypatch.setattr('src.main.load_profiles', mock_load_profiles)
        self.mock_load_profiles = mock_load_profiles # Store mock for assertion

    @pytest.fixture
    def mock_stdscr(self):
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80) # Mock terminal size
        return mock

    @pytest.fixture
    def mock_input(self, mock_stdscr):
        yield mock_stdscr.getstr, mock_stdscr.getch

    @pytest.fixture
    def mock_curses_init(self):
        with patch('curses.init_pair'), \
             patch('curses.curs_set'):
            yield

    @pytest.fixture
    def mock_os_geteuid(self):
        with patch('os.geteuid') as mock:
            yield mock

    @patch('src.main.curses.wrapper')
    def test_main_not_root(self, mock_wrapper, mock_os_geteuid, capsys, mock_stdscr):
        mock_os_geteuid.return_value = 1 # Not root
        result = main(mock_stdscr)
        assert result == "Error: This script must be run as root."
        mock_wrapper.assert_not_called()

    @patch('src.main.curses.wrapper')
    def test_main_terminal_too_small(self, mock_wrapper, mock_os_geteuid, mock_stdscr, capsys):
        mock_os_geteuid.return_value = 0 # Is root
        mock_stdscr.getmaxyx.return_value = (10, 20) # Too small
        mock_wrapper.side_effect = lambda func, *args, **kwargs: func(mock_stdscr)
        result = main(mock_stdscr)
        assert result == "Error: Terminal window is too small. Please resize to at least 80x24."
        mock_wrapper.assert_not_called()

    @patch('src.main.curses.wrapper')
    @patch('src.main.curses.curs_set')
    @patch('src.main.curses.init_pair')
    @patch('src.main.curses.color_pair')
    def test_main_success(self, mock_color_pair, mock_init_pair, mock_curs_set, mock_wrapper, mock_os_geteuid, mock_stdscr, mock_input):
        mock_os_geteuid.return_value = 0 # Is root
        mock_wrapper.side_effect = lambda func, *args, **kwargs: func(mock_stdscr)
        mock_init_pair.return_value = MagicMock()
        mock_curs_set.return_value = MagicMock()
        mock_color_pair.return_value = MagicMock()
        mock_input[1].side_effect = [curses.KEY_DOWN, curses.KEY_DOWN, curses.KEY_DOWN, curses.KEY_DOWN, curses.KEY_ENTER]
        mock_stdscr.attron = MagicMock()
        mock_stdscr.attroff = MagicMock()
    
        main(mock_stdscr)
        
        self.mock_load_profiles.assert_called_once()
        mock_curs_set.assert_called_once_with(0)
        mock_init_pair.assert_called_once_with(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        mock_color_pair.assert_called_with(1)