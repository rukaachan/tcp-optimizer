import curses
import os
import json

from src.config.profiles import load_profiles, get_active_profile
from src.network.sysctl import backup_settings, write_sysctl_config, apply_sysctl_from_conf, revert_settings, get_sysctl_value
from src.network.info import get_system_information

# --- Terminal User Interface (TUI) Functions ---

def draw_menu(stdscr, selected_row_idx, menu, title, active_profile=""):
    """Draws the menu with the selected item highlighted."""
    stdscr.clear(); h, w = stdscr.getmaxyx()
    stdscr.addstr(1, 2, title, curses.A_BOLD | curses.A_UNDERLINE)
    if active_profile:
        stdscr.addstr(2, 2, f"Current Profile: {active_profile}", curses.A_DIM)
    for idx, row in enumerate(menu):
        x = w//2 - len(row)//2; y = h//2 - len(menu)//2 + idx
        if idx == selected_row_idx:
            stdscr.attron(curses.color_pair(1)); stdscr.addstr(y, x, row); stdscr.attroff(curses.color_pair(1))
        else: stdscr.addstr(y, x, row)
    stdscr.refresh()

def display_message(stdscr, message, pause=True):
    """Displays a message in the center of the screen."""
    stdscr.clear(); h, w = stdscr.getmaxyx()
    y, x = h // 2, w // 2 - len(message) // 2
    stdscr.addstr(y, x, message)
    if pause: stdscr.addstr(h - 2, 2, "Press any key to continue..."); stdscr.getch()
    stdscr.refresh()

def get_confirmation(stdscr, prompt):
    """Gets a Yes/No confirmation from the user."""
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h - 4, 2, prompt + " (y/n)")
    stdscr.refresh()
    while True:
        key = stdscr.getch()
        if key in [ord('y'), ord('Y')]: return True
        if key in [ord('n'), ord('N')]: return False

def display_comparison_report(stdscr, before_params, after_params, before_speed={}, after_speed={}):
    """Shows a report comparing settings and performance before and after optimization."""
    stdscr.clear(); h, w = stdscr.getmaxyx()
    title = "Revert Report" if not before_speed else "Optimization Report: Before vs. After"
    stdscr.addstr(1, 2, title, curses.A_BOLD | curses.A_UNDERLINE)
    y_offset = 3
    if before_speed and after_speed:
        stdscr.addstr(y_offset, 2, "Performance Metrics", curses.A_BOLD); y_offset += 1
        stdscr.addstr(y_offset, 4, f"{'Metric':<12} {'Before':>15} {'After':>15} {'Change':>12}"); y_offset += 1
        stdscr.addstr(y_offset, 4, "-" * 56); y_offset += 1
        metrics = ['Download', 'Upload', 'Ping']
        for metric in metrics:
            before_val = before_speed.get(metric.lower(), 0); after_val = after_speed.get(metric.lower(), 0)
            unit = "Mbit/s" if metric != 'Ping' else "ms"
            change_pct = 0
            if before_val > 0: change_pct = ((before_val - after_val) / before_val) * 100 if metric == 'Ping' else ((after_val - before_val) / before_val) * 100
            color = curses.A_BOLD if change_pct > 1 else curses.color_pair(0)
            stdscr.addstr(y_offset, 4, f"{metric:<12} {before_val:>12.2f} {unit} {after_val:>12.2f} {unit}", color)
            stdscr.addstr(y_offset, 52, f"{change_pct:>+8.1f}%", color)
            y_offset += 1
        y_offset += 1
    stdscr.addstr(y_offset, 2, "Key Parameter Changes", curses.A_BOLD); y_offset += 1
    all_keys = sorted(list(set(before_params.keys()) | set(after_params.keys())))
    for param in all_keys:
        before_val = before_params.get(param, 'N/A'); after_val = after_params.get(param, 'N/A')
        if str(before_val) != str(after_val) and y_offset < h - 3:
            stdscr.addstr(y_offset, 4, f"{param.split('.')[-1]:<25}: {before_val} -> {after_val}", curses.A_BOLD)
            y_offset += 1
    stdscr.addstr(h - 2, 2, "Press any key to return to the main menu..."); stdscr.getch()

# --- Core Application Logic ---

def run_profile_benchmark(stdscr, profile_key, profiles_data, all_managed_params):
    display_message(stdscr, "Importing speedtest...", pause=False)
    try:
        import speedtest
    except ImportError:
        display_message(stdscr, "speedtest-cli is not installed. Please run 'sudo pip install speedtest-cli'")
        return
    display_message(stdscr, "Capturing current system state...", pause=False)
    key_params_to_check = ["net.ipv4.tcp_congestion_control", "net.ipv4.tcp_wmem", "net.ipv4.tcp_low_latency"]
    before_params = {p: get_sysctl_value(p) for p in key_params_to_check if get_sysctl_value(p)}
    display_message(stdscr, "Running 'Before' speed test (this can take a minute)...", pause=False)
    try:
        s = speedtest.Speedtest(secure=True); s.get_best_server(); s.download(); s.upload()
        before_results = s.results.dict()
        before_speed = {'download': before_results['download'] / 1_000_000, 'upload': before_results['upload'] / 1_000_000, 'ping': before_results['ping']}
    except Exception as e: display_message(stdscr, f"Error during 'Before' speed test: {e}"); return
    display_message(stdscr, f"Applying '{profile_key}' profile...", pause=False)
    backup_settings(ALL_MANAGED_PARAMS)
    if profiles_data is None or profile_key not in profiles_data:
        display_message(stdscr, "Profile data is not available or invalid.")
        return
    write_sysctl_config(profiles_data[profile_key]["settings"])
    apply_sysctl_from_conf()
    after_params = {p: get_sysctl_value(p) for p in key_params_to_check if get_sysctl_value(p)}
    display_message(stdscr, "Running 'After' speed test to measure improvement...", pause=False)
    try:
        s = speedtest.Speedtest(secure=True); s.get_best_server(); s.download(); s.upload()
        after_results = s.results.dict()
        after_speed = {'download': after_results['download'] / 1_000_000, 'upload': after_results['upload'] / 1_000_000, 'ping': after_results['ping']}
    except Exception as e:
        display_message(stdscr, f"Error during 'After' speed test: {e}")
        display_comparison_report(stdscr, before_params, after_params, before_speed, {}); return
    display_comparison_report(stdscr, before_params, after_params, before_speed, after_speed)

def revert_and_show_report(stdscr):
    """Reverts settings to original state and shows a comparison report."""
    if not os.path.exists("/etc/sysctl.d/tcp-optimizer.conf.bak"):
        display_message(stdscr, "No backup file found. Cannot revert."); return
    try:
        with open("/etc/sysctl.d/tcp-optimizer.conf.bak", 'r') as f: after_settings = json.load(f)
    except json.JSONDecodeError:
        display_message(stdscr, "Error: The backup file is corrupted. Cannot revert."); return
    before_settings = {}
    if os.path.exists("/etc/sysctl.d/tcp-optimizer.conf"):
        with open("/etc/sysctl.d/tcp-optimizer.conf", 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = [x.strip() for x in line.split('=', 1)]; before_settings[key] = value
    else: before_settings = after_settings
    
    # Call the revert function from system_utils
    revert_message = revert_settings()
    
    # Display the report and the final message
    display_comparison_report(stdscr, before_settings, after_settings)
    display_message(stdscr, revert_message)


def analyze_and_apply(stdscr):
    """Analyzes network performance to recommend and apply a suitable profile."""
    display_message(stdscr, "Running analysis to recommend a profile...", pause=False)
    try:
        import speedtest
        s = speedtest.Speedtest(secure=True); s.get_best_server(); s.download()
        download_speed = s.results.dict()['download'] / 1_000_000
        if download_speed > 1000: profile_key = "high_speed"
        elif download_speed < 50: profile_key = "gaming"
        else: profile_key = "balanced"
        
        prompt = f"Analysis complete. Recommended profile: '{profile_key}'. Apply and benchmark?"
        if get_confirmation(stdscr, prompt):
            # Pass profiles_data and all_managed_params to run_profile_benchmark
            run_profile_benchmark(stdscr, profile_key, PROFILES, ALL_MANAGED_PARAMS)

    except Exception as e:
        display_message(stdscr, f"Could not complete analysis: {e}. Please choose a profile manually.")

# --- Menu Navigation Functions ---

def main_menu(stdscr, profiles_data, all_managed_params):
    """Handles the main menu navigation and options."""
    menu = ["Analyze Network & Apply Optimal Settings", "Apply Pre-defined Profile (with Benchmark)", "System Information", "Revert to Original Defaults", "Exit"]
    current_row = 0
    while True:
        active_profile = get_active_profile(profiles_data)
        draw_menu(stdscr, current_row, menu, "Linux TCP Optimizer [Refined]", active_profile)
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0: current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1: current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0: analyze_and_apply(stdscr)
            # Pass profiles_data and all_managed_params to profiles_menu
            elif current_row == 1: profiles_menu(stdscr, profiles_data, all_managed_params)
            elif current_row == 2: display_system_info(stdscr)
            elif current_row == 3: revert_and_show_report(stdscr)
            elif current_row == 4: break

def profiles_menu(stdscr, profiles_data, all_managed_params):
    """Handles the submenu for selecting pre-defined profiles."""
    if profiles_data is None:
        display_message(stdscr, "Profiles are not loaded. Cannot display profiles menu.")
        return
    profile_keys = list(profiles_data.keys())
    menu_items = [f"{key.replace('_', ' ').title()}" for key in profile_keys]
    menu_items.append("Back"); current_row = 0
    while True:
        stdscr.clear(); h, w = stdscr.getmaxyx()
        title = "Apply & Benchmark a Pre-defined Profile"
        stdscr.addstr(1, 2, title, curses.A_BOLD | curses.A_UNDERLINE)
        for idx, row in enumerate(menu_items):
            x = w//2 - len(row)//2; y = h//2 - len(menu_items)//2 + idx
            if idx == current_row:
                stdscr.attron(curses.color_pair(1)); stdscr.addstr(y, x, row); stdscr.attroff(curses.color_pair(1))
            else: stdscr.addstr(y, x, row)
        if current_row < len(profile_keys):
            desc = profiles_data.get(selected_key, {}).get('description', 'No description available.')
            stdscr.addstr(h - 3, w//2 - len(desc)//2, desc, curses.A_DIM)
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0: current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu_items) - 1: current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row < len(profile_keys):
                profile_key = profile_keys[current_row]
                # Pass profiles_data and all_managed_params to run_profile_benchmark
                run_profile_benchmark(stdscr, profile_key, profiles_data, all_managed_params)
            else: break

def display_system_info(stdscr):
    """Displays system information."""
    info = get_system_information()
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    y_offset = 2
    stdscr.addstr(1, 2, "System Information", curses.A_BOLD | curses.A_UNDERLINE)
    for key, value in info.items():
        if y_offset < h - 3:
            stdscr.addstr(y_offset, 4, f"{key:<25}: {value}")
            y_offset += 1
    stdscr.addstr(h - 2, 2, "Press any key to return to the main menu...")
    stdscr.getch()

def main(stdscr):
    """Initializes the TUI and checks system requirements."""
    if os.geteuid() != 0:
        return "Error: This script must be run as root."
    
    h, w = stdscr.getmaxyx()
    if h < 24 or w < 80:
        return "Error: Terminal window is too small. Please resize to at least 80x24."

    curses.curs_set(0); curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # Load profiles and managed parameters inside main function
    PROFILES = load_profiles()
    if not PROFILES:
        print(f"Error: 'profiles.json' not found or is corrupted. Please ensure it is in the same directory.")
        exit(1)
    
    ALL_MANAGED_PARAMS = sorted(list(set(p for profile in PROFILES.values() for p in profile['settings'].keys())))

    main_menu(stdscr, PROFILES, ALL_MANAGED_PARAMS)
    return "Application exited normally."

if __name__ == "__main__":
    error_message = curses.wrapper(main)
    if "Error" in error_message:
        print(error_message)