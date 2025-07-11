#!/usr/bin/env python3

# main.py
# Main file for the Linux TCP Optimizer tool.

import curses
import os
import json
import re
import statistics
import subprocess
import threading
import time
import system_utils as su
import nic_utils as nu

# --- Configuration ---
DAEMON_STATUS_FILE = "/tmp/tcp_optimizer_daemon.status"
SERVICE_NAME = "tcp-optimizer.service"

# --- Load Profiles Data on Startup ---
PROFILES = su.load_profiles()
if not PROFILES:
    print(f"Error: '{su.PROFILES_FILE}' not found or is corrupted.")
    exit(1)

ALL_MANAGED_PARAMS = sorted(list(set(p for profile in PROFILES.values() for p in profile.get('settings', {}).keys())))

# --- Latency & Bufferbloat Testing ---

class PingTest(threading.Thread):
    def __init__(self, host="8.8.8.8"):
        super().__init__(); self.host, self.latencies, self.stop_event, self.daemon = host, [], threading.Event(), True
    def run(self):
        try:
            process = subprocess.Popen(["ping", self.host, "-i", "0.2"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.stdout:
                while not self.stop_event.is_set():
                    line = process.stdout.readline()
                    if not line:
                        break
                    if match := re.search(r"time=([\d.]+)\s*ms", line):
                        self.latencies.append(float(match.group(1)))
            process.terminate()
        except (IOError, OSError): pass
    def stop(self): self.stop_event.set()

def run_full_benchmark(stdscr):
    results = {'download': 0, 'upload': 0, 'ping': 0, 'idle_latency': 0, 'loaded_latency': 0}
    import speedtest
    ping_test = PingTest(); ping_test.start()
    display_message(stdscr, "Measuring idle latency (5s)...", pause=False); time.sleep(5)
    idle_latencies = ping_test.latencies.copy(); ping_test.latencies.clear()
    display_message(stdscr, "Running speed test...", pause=False)
    try:
        s = speedtest.Speedtest(secure=True); s.get_best_server(); s.download(); s.upload()
        sr = s.results.dict(); results.update({'download': sr['download'] / 1e6, 'upload': sr['upload'] / 1e6, 'ping': sr['ping']})
    except Exception as e: ping_test.stop(); display_message(stdscr, f"Speed test failed: {e}"); return None
    loaded_latencies = ping_test.latencies.copy(); ping_test.stop()
    if idle_latencies: results['idle_latency'] = statistics.mean(idle_latencies)
    if loaded_latencies: results['loaded_latency'] = statistics.mean(loaded_latencies)
    return results

# --- TUI Functions ---

def draw_menu(stdscr, selected_row_idx, menu, title, active_profile=""):
    stdscr.clear(); h, w = stdscr.getmaxyx()
    stdscr.addstr(1, 2, title, curses.A_BOLD | curses.A_UNDERLINE)
    if active_profile: stdscr.addstr(2, 2, f"Current Profile: {active_profile}", curses.A_DIM)
    for idx, row in enumerate(menu):
        x, y = w//2 - len(row)//2, h//2 - len(menu)//2 + idx
        stdscr.addstr(y, x, row, curses.color_pair(1) if idx == selected_row_idx else curses.A_NORMAL)
    stdscr.refresh()

def display_message(stdscr, message, pause=True, wrap=True):
    stdscr.clear(); h, w = stdscr.getmaxyx()
    if wrap:
        lines = [message[i:i+w-4] for i in range(0, len(message), w-4)]
        for i, line in enumerate(lines):
            stdscr.addstr(h//2 - len(lines)//2 + i, w//2 - len(line)//2, line)
    else: stdscr.addstr(h//2, w//2 - len(message)//2, message)
    if pause: stdscr.addstr(h - 2, 2, "Press any key..."); stdscr.getch()
    stdscr.refresh()

def get_confirmation(stdscr, prompt):
    h, w = stdscr.getmaxyx(); stdscr.addstr(h - 4, 2, prompt + " (y/n)"); stdscr.refresh()
    while True:
        if (key := stdscr.getch()) in [ord('y'), ord('Y')]: return True
        if key in [ord('n'), ord('N')]: return False

def display_comparison_report(stdscr, data):
    stdscr.clear(); h, w = stdscr.getmaxyx(); y_offset = 2
    stdscr.addstr(0, 2, "Optimization Report", curses.A_BOLD | curses.A_UNDERLINE)
    if data.get('before_results') and data.get('after_results'):
        stdscr.addstr(y_offset, 2, "Performance Metrics", curses.A_BOLD); y_offset += 1
        stdscr.addstr(y_offset, 4, f"{'Metric':<18} {'Before':>15} {'After':>15} {'Change':>15}"); y_offset += 1; stdscr.addstr(y_offset, 4, "-" * 65); y_offset += 1
        for name, unit, lower_is_better in [('Download', 'Mbit/s', False), ('Upload', 'Mbit/s', False), ('Idle Latency', 'ms', True), ('Loaded Latency', 'ms', True)]:
                key = name.lower().replace(' ', '_')
                b = data['before_results'].get(key, 0)
                a = data['after_results'].get(key, 0)
                change = ((a - b) / b) * 100 if b > 0 else 0
                if lower_is_better: change *= -1
                color = curses.A_BOLD if abs(change) > 1 else curses.A_NORMAL
                stdscr.addstr(y_offset, 4, f"{name:<18} {b:>10.2f} {unit} {a:>10.2f} {unit}", color); stdscr.addstr(y_offset, 55, f"{change:>+10.1f}%", color); y_offset += 1
        y_offset += 1
        for title, params_key in [("Sysctl Changes", "sysctl"), ("NIC Driver Changes", "nic")]:
            changed_items = {k: (v.get('before'), v.get('after')) for k, v in data.get(params_key, {}).items() if isinstance(v, dict) and v.get('before') != v.get('after')}
            if not changed_items: continue
            stdscr.addstr(y_offset, 2, title, curses.A_BOLD); y_offset += 1
            for param, (val_b, val_a) in changed_items.items():
                if y_offset >= h - 2: break
                stdscr.addstr(y_offset, 4, f"{param:<25}: {val_b} -> {val_a}", curses.A_BOLD); y_offset += 1
        y_offset += 1
    stdscr.addstr(h - 2, 2, "Press any key..."); stdscr.getch()

# --- Core Application Logic ---

def run_profile_benchmark(stdscr, profile_key):
    if not PROFILES:
        display_message(stdscr, "Profiles data not loaded.")
        return
    profile = PROFILES.get(profile_key)
    if not profile:
        display_message(stdscr, f"Profile '{profile_key}' not found.")
        return

    sysctl_s = profile.get("settings", {})
    ethtool_s = profile.get("ethtool_settings", {})
    report_data = {"sysctl": {}, "nic": {}}

    display_message(stdscr, "Capturing 'before' state...", pause=False)
    for p in sysctl_s:
        report_data["sysctl"][p] = {'before': su.get_sysctl_value(p), 'after': ''}

    active_nic = nu.get_active_nic()
    if active_nic and ethtool_s:
        before_nic_full = nu.get_ring_buffer(active_nic)
        if before_nic_full:
            before_nic = before_nic_full['current']
            for p in ethtool_s:
                report_data["nic"][p] = {'before': before_nic.get(p, 'N/A'), 'after': ''}

    before_results = run_full_benchmark(stdscr)
    if not before_results:
        before_results = {}
    report_data['before_results'] = before_results

    if not get_confirmation(stdscr, f"Apply '{profile_key}' and run 'After' benchmark?"):
        return

    display_message(stdscr, f"Applying '{profile_key}' profile...", pause=False)
    su.backup_settings(ALL_MANAGED_PARAMS)
    su.write_sysctl_config(sysctl_s)
    su.apply_sysctl_from_conf()

    if active_nic and ethtool_s:
        nu.backup_ethtool_settings(active_nic)
        max_nic_full = nu.get_ring_buffer(active_nic)
        if max_nic_full:
            max_nic = max_nic_full['max']
            rx = max_nic['rx'] if ethtool_s.get('rx') == 'max' else ethtool_s['rx']
            tx = max_nic['tx'] if ethtool_s.get('tx') == 'max' else ethtool_s['tx']
            nu.set_ring_buffer(active_nic, rx, tx)

    for p in sysctl_s:
        report_data["sysctl"][p]['after'] = su.get_sysctl_value(p)

    if active_nic and ethtool_s:
        after_nic_full = nu.get_ring_buffer(active_nic)
        if after_nic_full:
            after_nic = after_nic_full['current']
            for p in ethtool_s:
                report_data["nic"][p]['after'] = after_nic.get(p, 'N/A')

    after_results = run_full_benchmark(stdscr)
    if not after_results:
        display_message(stdscr, "'After' benchmark failed.")
    report_data['after_results'] = after_results or {}
    display_comparison_report(stdscr, report_data)

def revert_and_show_report(stdscr):
    if os.path.exists(su.BACKUP_FILE): display_message(stdscr, su.revert_settings())
    else: display_message(stdscr, "No sysctl backup found.")
    if os.path.exists(nu.ETHTOOL_BACKUP_FILE): nu.revert_ethtool_settings(nu.get_active_nic()); display_message(stdscr, "NIC settings reverted.")

def analyze_and_apply(stdscr):
    results = run_full_benchmark(stdscr)
    if not results: return
    bufferbloat = results['loaded_latency'] - results['idle_latency']
    profile_key = "gaming" if bufferbloat > 50 else "high_speed" if results['download'] > 800 else "balanced"
    if get_confirmation(stdscr, f"DL: {results['download']:.0f}Mb/s, Bufferbloat: {bufferbloat:.0f}ms. Recommend: '{profile_key}'. Apply?"): run_profile_benchmark(stdscr, profile_key)

# --- Menu Navigation & Daemon Management ---

def run_system_command(stdscr, command):
    try: output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e: output = e.output
    display_message(stdscr, output, wrap=False)

def daemon_menu(stdscr):
    menu = ["Enable & Start Daemon", "Disable & Stop Daemon", "Check Daemon Status", "Back"]
    current_row = 0
    while True:
        draw_menu(stdscr, current_row, menu, "Manage Real-time Daemon")
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0: current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1: current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0: run_system_command(stdscr, f"sudo systemctl enable --now {SERVICE_NAME}")
            elif current_row == 1: run_system_command(stdscr, f"sudo systemctl disable --now {SERVICE_NAME}")
            elif current_row == 2: run_system_command(stdscr, f"sudo systemctl status {SERVICE_NAME}")
            elif current_row == 3: break

def get_daemon_status():
    if not os.path.exists(DAEMON_STATUS_FILE): return None
    try:
        with open(DAEMON_STATUS_FILE, 'r') as f:
            status = json.load(f)
        if isinstance(status, dict):
            return f"Daemon Active ({status.get('active_profile', '...').title()})"
        else:
            return "Daemon Status Corrupted: Invalid JSON format"
    except (json.JSONDecodeError, IOError): return "Daemon Status Corrupted"

def main_menu(stdscr):
    menu = ["Analyze & Apply Manually", "Apply Profile & Benchmark", "Manage Real-time Daemon", "Revert All Settings", "Exit"]
    current_row = 0
    while True:
        active_status = (get_daemon_status() or su.get_active_profile(PROFILES)) or "No Active Profile"
        draw_menu(stdscr, current_row, menu, "Linux TCP Optimizer", active_status)
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0: current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1: current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0: analyze_and_apply(stdscr)
            elif current_row == 1: profiles_menu(stdscr)
            elif current_row == 2: daemon_menu(stdscr)
            elif current_row == 3: revert_and_show_report(stdscr)
            elif current_row == 4: break

def profiles_menu(stdscr):
    if not PROFILES:
        display_message(stdscr, "Profiles data not loaded.")
        return
    profile_keys = list(PROFILES.keys())
    menu_items = [f"{key.replace('_', ' ').title()}" for key in profile_keys] + ["Back"]
    current_row = 0
    while True:
        draw_menu(stdscr, current_row, menu_items, "Apply & Benchmark a Profile")
        if current_row < len(profile_keys):
            profile_key = profile_keys[current_row]
            if profile_key in PROFILES:
                desc = PROFILES[profile_key].get('description', '')
                stdscr.addstr(curses.LINES - 3, 2, desc, curses.A_DIM)
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0: current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu_items) - 1: current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row < len(profile_keys): run_profile_benchmark(stdscr, profile_keys[current_row])
            else: break

def main(stdscr):
    if os.geteuid() != 0: return "Error: Must be run as root."
    if curses.LINES < 24 or curses.COLS < 80: return "Error: Terminal too small."
    curses.curs_set(0); curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    main_menu(stdscr)
    return "Application exited."

if __name__ == "__main__": print(curses.wrapper(main))
