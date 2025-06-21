# index.py
# Main file for the Linux TCP Optimizer tool.

import curses
import os
import json
import system_utils as su  # Import system utilities module

# --- Load Profiles Data on Startup ---
PROFILES = su.load_profiles()
if not PROFILES:
    print(f"Error: '{su.PROFILES_FILE}' not found or is corrupted. Please ensure it is in the same directory.")
    exit(1)

# List of all parameters managed by profiles for backup.
ALL_MANAGED_PARAMS = sorted(list(set(p for profile in PROFILES.values() for p in profile['settings'].keys())))

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

def display_comparison_report(stdscr, before_params, after_params, before_speed={}, after_speed={}, profile_settings=None):
    """
    Shows a comprehensive report comparing system parameters and network performance
    before and after an optimization profile is applied or settings are reverted.

    Args:
        stdscr: The curses screen object for drawing.
        before_params (dict): System parameters captured before changes.
        after_params (dict): System parameters captured after changes.
        before_speed (dict, optional): Speedtest results before changes. Defaults to {}.
        after_speed (dict, optional): Speedtest results after changes. Defaults to {}.
        profile_settings (dict, optional): The settings dictionary of the applied profile.
            If provided, the report will show expected values and highlight discrepancies.
            If None or empty (e.g., for revert), it falls back to a simpler comparison.

    The report dynamically adjusts its title and parameter display logic based on whether
    `profile_settings` are available. When available, it highlights:
    - Parameters that successfully changed to the expected value (Bold).
    - Parameters that did not change to the expected value (Bold, with "Expected:..." note).
    - Parameters that were already at the expected value or did not change (Dim).
    For reverts, it shows a list of parameters that were changed back.
    """
    stdscr.clear(); h, w = stdscr.getmaxyx()
    y_offset = 3

    # Determine title based on context
    if not profile_settings: # Handles profile_settings being None or empty dict
        title = "Revert Report: Old vs. Restored"
    elif not before_speed and not after_speed:
        title = "Parameter Change Report" # e.g. if speedtest failed/skipped but profile was applied
    else:
        title = "Optimization Report: Before vs. After"
    stdscr.addstr(1, 2, title, curses.A_BOLD | curses.A_UNDERLINE)

    # Display Performance Metrics if available
    if before_speed and after_speed: # Typically available for benchmark runs
        stdscr.addstr(y_offset, 2, "Performance Metrics", curses.A_BOLD); y_offset += 1
        stdscr.addstr(y_offset, 4, f"{'Metric':<12} {'Before':>15} {'After':>15} {'Change':>12}"); y_offset += 1
        stdscr.addstr(y_offset, 4, "-" * 56); y_offset += 1
        metrics = ['Download', 'Upload', 'Ping']
        for metric in metrics:
            before_val = before_speed.get(metric.lower(), 0); after_val = after_speed.get(metric.lower(), 0)
            unit = "Mbit/s" if metric != 'Ping' else "ms"
            change_pct = 0
            if metric == 'Ping': # Lower is better for Ping
                if before_val > 0: change_pct = ((before_val - after_val) / before_val) * 100
            else: # Higher is better for Download/Upload
                if before_val > 0: change_pct = ((after_val - before_val) / before_val) * 100

            # Determine color based on positive/negative change (green for good, red for bad)
            # For now, just bold if any significant change.
            color_attr = curses.A_BOLD if abs(change_pct) > 1 else curses.color_pair(0)
            stdscr.addstr(y_offset, 4, f"{metric:<12} {before_val:>12.2f} {unit} {after_val:>12.2f} {unit}", color_attr)
            stdscr.addstr(y_offset, 52, f"{change_pct:>+8.1f}%", color_attr)
            y_offset += 1
        y_offset += 1

    # Display Key Parameter Changes
    # Title of this section depends on whether we are showing a profile application or a revert.
    section_title = "Key Parameter Changes (Profile vs. Actual)" if profile_settings else "Reverted Parameters"
    stdscr.addstr(y_offset, 2, section_title, curses.A_BOLD); y_offset += 1

    if profile_settings: # If profile_settings is provided (typically for benchmark/apply profile case)
        # Iterate through parameters defined in the profile to compare expected vs. actual.
        for param_name in sorted(profile_settings.keys()):
            if y_offset >= h - 3: break # Ensure we don't write past the screen (leave room for last line)

            expected_value = str(profile_settings[param_name])
            value_before = str(before_params.get(param_name, 'N/A (Not previously tracked)'))
            value_after = str(after_params.get(param_name, 'N/A (Not set by profile)'))

            display_str = f"{param_name.split('.')[-1]:<25}: {value_before} -> {value_after}"
            attr = curses.A_NORMAL

            if value_after != expected_value and value_after != 'N/A (Not set by profile)':
                # Parameter was set, but not to the expected value
                display_str += f" (Expected: {expected_value})"
                attr = curses.A_BOLD # Highlight unexpected outcome
            elif value_before == value_after and value_after != expected_value :
                # Parameter was not changed by the profile application, but it's not the expected value.
                # This implies it was already different from the profile's recommendation.
                 display_str += f" (Expected: {expected_value})"
                 attr = curses.A_DIM # Dim as it wasn't an active change, but note expectation.
            elif value_before == value_after:
                # Parameter was not changed, and it matches the expected value (or was N/A and remains so).
                # Or, parameter was not in profile_settings but is being compared (less likely here).
                attr = curses.A_DIM # De-emphasize parameters that didn't need to change or didn't change.
            else:
                # Successful change to the expected value (or at least, it changed).
                attr = curses.A_BOLD

            stdscr.addstr(y_offset, 4, display_str, attr)
            y_offset += 1
    else: # Fallback for revert report or if profile_settings is None/empty.
          # This shows a simple before/after comparison based on captured states.
        all_keys = sorted(list(set(before_params.keys()) | set(after_params.keys())))
        for param_name in all_keys:
            if y_offset >= h - 3: break # Ensure we don't write past the screen

            value_before = str(before_params.get(param_name, 'N/A'))
            value_after = str(after_params.get(param_name, 'N/A'))

            if value_before != value_after: # Only show parameters that actually changed
                display_str = f"{param_name.split('.')[-1]:<25}: {value_before} -> {value_after}"
                stdscr.addstr(y_offset, 4, display_str, curses.A_BOLD)
                y_offset += 1
            elif title == "Revert Report: Old vs. Restored": # In revert, show even if same if it was part of backup
                # This part can be tricky: after_settings are the backed-up values.
                # before_settings are current values before revert.
                # We want to show what was restored.
                 display_str = f"{param_name.split('.')[-1]:<25}: {value_before} (Current) -> {value_after} (Restored)"
                 stdscr.addstr(y_offset, 4, display_str, curses.A_DIM) # Dim if no change
                 y_offset +=1


    stdscr.addstr(h - 2, 2, "Press any key to return to the main menu..."); stdscr.getch()

# --- Core Application Logic ---

def run_profile_benchmark(stdscr, profile_key):
    """
    Runs speed tests before and after applying a specified TCP optimization profile
    and displays a detailed comparison report.

    The function performs the following key actions:
    1.  Retrieves the settings for the given `profile_key`.
    2.  Dynamically captures the current values of parameters defined in the profile's settings (`before_params`).
    3.  Runs a speedtest to establish baseline performance (`before_speed`).
    4.  Applies the profile settings to the system.
    5.  Dynamically captures the new values of the same parameters (`after_params`).
    6.  Runs another speedtest to measure performance after applying the profile (`after_speed`).
    7.  Calls `display_comparison_report` with all captured data, including `profile_settings`
        for detailed comparison against expected values.

    Args:
        stdscr: The curses screen object.
        profile_key (str): The key identifying the profile to benchmark (e.g., "balanced", "gaming").
    """
    display_message(stdscr, "Importing speedtest...", pause=False)
    try:
        import speedtest
    except ImportError:
        display_message(stdscr, "speedtest-cli is not installed. Please run 'sudo pip install speedtest-cli'")
        return

    # Retrieve the settings for the chosen profile.
    display_message(stdscr, "Loading profile settings...", pause=False) # Added user feedback
    if PROFILES is None or profile_key not in PROFILES:
        display_message(stdscr, "Profile data is not available or invalid.")
        return
    profile_settings = PROFILES[profile_key].get("settings", {})
    if not profile_settings:
        display_message(stdscr, f"No settings found for profile '{profile_key}'. Cannot benchmark.")
        return

    # Dynamically capture current values for parameters listed in the profile.
    display_message(stdscr, "Capturing 'before' system state based on profile...", pause=False)
    before_params = {}
    for param_name in profile_settings.keys(): # Iterate only over keys in the profile
        try:
            value = su.get_sysctl_value(param_name)
            before_params[param_name] = value if value else 'N/A (empty)'
        except Exception as e:
            before_params[param_name] = f'N/A (error: {e})' # Store error if param cannot be read

    # Run speed test before applying any changes.
    display_message(stdscr, "Running 'Before' speed test (this can take a minute)...", pause=False)
    try:
        s = speedtest.Speedtest(secure=True); s.get_best_server(); s.download(); s.upload()
        before_results = s.results.dict()
        before_speed = {'download': before_results['download'] / 1_000_000, 'upload': before_results['upload'] / 1_000_000, 'ping': before_results['ping']}
    except Exception as e:
        display_message(stdscr, f"Error during 'Before' speed test: {e}"); return

    display_message(stdscr, f"Applying '{profile_key}' profile...", pause=False)
    su.backup_settings(ALL_MANAGED_PARAMS) # Backup settings before applying new ones

    # Apply the profile settings
    su.write_sysctl_config(profile_settings)
    su.apply_sysctl_from_conf()

    # Dynamically capture new values for the same parameters after applying the profile.
    display_message(stdscr, "Capturing 'after' system state...", pause=False) # Added user feedback
    after_params = {}
    for param_name in profile_settings.keys(): # Iterate only over keys relevant to the applied profile
        try:
            value = su.get_sysctl_value(param_name)
            after_params[param_name] = value if value else 'N/A (empty)'
        except Exception as e:
            after_params[param_name] = f'N/A (error: {e})' # Store error if param cannot be read

    # Run speed test after applying changes to measure impact.
    display_message(stdscr, "Running 'After' speed test to measure improvement...", pause=False)
    try:
        s = speedtest.Speedtest(secure=True); s.get_best_server(); s.download(); s.upload()
        after_results = s.results.dict()
        after_speed = {'download': after_results['download'] / 1_000_000, 'upload': after_results['upload'] / 1_000_000, 'ping': after_results['ping']}
    except Exception as e:
        display_message(stdscr, f"Error during 'After' speed test: {e}")
        display_comparison_report(stdscr, before_params, after_params, before_speed, {}, profile_settings); return
    # Display the comprehensive comparison report, passing profile_settings for detailed diff.
    display_comparison_report(stdscr, before_params, after_params, before_speed, after_speed, profile_settings)

def revert_and_show_report(stdscr):
    """
    Reverts system settings from a backup file to their original state (before any profile
    was applied) and shows a report of the changes.

    The backup file is expected to be created by `su.backup_settings()`.
    The report shown uses `display_comparison_report` with `profile_settings={}` to trigger
    its fallback display logic, suitable for showing reverted parameters.
    """
    if not os.path.exists(su.BACKUP_FILE):
        display_message(stdscr, "No backup file found. Cannot revert."); return
    try:
        with open(su.BACKUP_FILE, 'r') as f: after_settings = json.load(f)
    except json.JSONDecodeError:
        display_message(stdscr, "Error: The backup file is corrupted. Cannot revert."); return
    before_settings = {}
    if os.path.exists(su.SYSCTL_CONF_FILE):
        with open(su.SYSCTL_CONF_FILE, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = [x.strip() for x in line.split('=', 1)]; before_settings[key] = value
    else: before_settings = after_settings
    
    # Call the revert function from system_utils
    revert_message = su.revert_settings()
    
    # Display the report and the final message.
    # Pass an empty dict for profile_settings to trigger fallback/revert logic in display_comparison_report.
    display_comparison_report(stdscr, before_settings, after_settings, profile_settings={})
    display_message(stdscr, revert_message)


def analyze_and_apply(stdscr):
    """
    Analyzes current network performance (download speed) to recommend a suitable
    TCP optimization profile and offers to apply it with a benchmark.

    Requires `speedtest-cli` to be installed.
    If confirmed by the user, it calls `run_profile_benchmark` for the recommended profile.
    """
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
            run_profile_benchmark(stdscr, profile_key)

    except Exception as e:
        display_message(stdscr, f"Could not complete analysis: {e}. Please choose a profile manually.")

# --- Menu Navigation Functions ---

def main_menu(stdscr):
    """Handles the main menu navigation and options."""
    menu = ["Analyze Network & Apply Optimal Settings", "Apply Pre-defined Profile (with Benchmark)", "Revert to Original Defaults", "Exit"]
    current_row = 0
    while True:
        active_profile = su.get_active_profile(PROFILES)
        draw_menu(stdscr, current_row, menu, "Linux TCP Optimizer [Refined]", active_profile)
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0: current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1: current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0: analyze_and_apply(stdscr)
            elif current_row == 1: profiles_menu(stdscr)
            elif current_row == 2: revert_and_show_report(stdscr)
            elif current_row == 3: break

def profiles_menu(stdscr):
    """Handles the submenu for selecting pre-defined profiles."""
    if PROFILES is None:
        display_message(stdscr, "Profiles are not loaded. Cannot display profiles menu.")
        return
    profile_keys = list(PROFILES.keys())
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
            selected_key = profile_keys[current_row]
            desc = PROFILES.get(selected_key, {}).get('description', 'No description available.')
            stdscr.addstr(h - 3, w//2 - len(desc)//2, desc, curses.A_DIM)
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0: current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu_items) - 1: current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row < len(profile_keys):
                profile_key = profile_keys[current_row]
                run_profile_benchmark(stdscr, profile_key)
            else: break

# --- Main Entry Point ---

def main(stdscr):
    """Initializes the TUI and checks system requirements."""
    if os.geteuid() != 0:
        return "Error: This script must be run as root."
    
    h, w = stdscr.getmaxyx()
    if h < 24 or w < 80:
        return "Error: Terminal window is too small. Please resize to at least 80x24."

    curses.curs_set(0); curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    main_menu(stdscr)
    return "Application exited normally."

if __name__ == "__main__":
    error_message = curses.wrapper(main)
    if "Error" in error_message:
        print(error_message)
