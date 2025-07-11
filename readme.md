# Linux TCP Optimizer Suite

A comprehensive Python-based suite for analyzing, benchmarking, and dynamically optimizing network performance on Linux systems.

This tool goes beyond simple `sysctl` tuning by incorporating advanced bufferbloat analysis, NIC driver-level tuning, and an optional real-time daemon that adapts your network settings based on your current activity.

## Key Features

- **Advanced Benchmarking:** Measures not only download/upload speed but also **latency under load** to accurately diagnose and quantify bufferbloat. Requires `speedtest-cli` to be installed (included in `requirements.txt`).
- **Multi-Layer Tuning:** Optimizes performance at both the kernel level (`sysctl`) and the NIC driver level (`ethtool` ring buffers).
- **Profile-Based System:** Comes with pre-defined profiles for different use cases (e.g., Gaming, High-Speed Fiber, Streaming) that are easily customizable.
- **Real-time Adaptive Daemon:** An optional `systemd` service that runs in the background, automatically switching to the best network profile based on the applications you are running (e.g., applies the 'Gaming' profile when Steam is launched).
- **Interactive TUI:** A user-friendly Terminal User Interface for easy manual benchmarking, profile application, and daemon management.
- **Safe & Reversible:** All changes are easily revertible to the original system state.

## Installation

This project requires Python 3.8 or higher.

1.  **Clone the repository:**

    ```bash
    https://github.com/rukaachan/tcp-optimizer
    cd tcp-optimizer
    ```

2.  **Install dependencies:**
    ```bash
    # It is recommended to do this inside a Python virtual environment
    python3 -m pip install -r requirements.txt
    ```

## Uninstallation

To completely remove the `tcp-optimizer` service and its associated files, run the `uninstall.sh` script with root privileges:

```bash
sudo ./uninstall.sh
```

This will stop and disable the `systemd` service, remove the service file, and delete any backup or configuration files created by the optimizer.

## Testing

To run the automated tests, first ensure you have installed the development dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Then, navigate to the project root and run pytest:

```bash
pytest
```

This will execute all tests in the `tests/` directory, verifying the core functionality of the utility modules.

## Usage

This suite can be used in two modes: **Manual Mode** (via the TUI) or **Automated Mode** (via the daemon).

### Manual Mode (TUI)

For one-time analysis, benchmarking, and profile application, run the main script with root privileges.

```bash
sudo python3 main.py
```

This will launch the Terminal User Interface with the following options:

- **Analyze & Apply Manually:** Runs a full benchmark and recommends the best profile based on your connection's speed and bufferbloat.
- **Apply Profile & Benchmark:** Manually choose a profile to apply and see a detailed before-and-after comparison report.
- **Manage Real-time Daemon:** Control the automated daemon (see below).
- **Revert All Settings:** Safely restores your system's original network settings.

### Automated Mode (Real-time Daemon)

For a "set it and forget it" experience, you can enable the `systemd` service to have the daemon manage your profiles automatically.

**1. Run the Installer:**

The provided `install.sh` script handles the service installation automatically. It will configure the necessary paths and move the service file to the correct location.

```bash
# Run the installer with root privileges
sudo ./install.sh
```

**2. Manage the Service:**

You can now manage the daemon using standard `systemctl` commands or through the **Manage Real-time Daemon** menu in the TUI.

- **Enable and Start:**
  ```bash
  sudo systemctl enable --now tcp-optimizer.service
  ```
- **Check Status:**
  ```bash
  sudo systemctl status tcp-optimizer.service
  ```
- **Stop and Disable:**
  ```bash
  sudo systemctl disable --now tcp-optimizer.service
  ```

## Configuration

The behavior of the optimizer is controlled by the `profiles.json` file.

- **`profiles`:**
  - Define the `sysctl` kernel parameters for each profile.
  - Add `ethtool_settings` to profiles to control NIC ring buffers. Setting `"rx": "max"` will intelligently use the maximum value supported by your hardware.

- **`daemon_config`:**
  - **`check_interval`**: How often (in seconds) the daemon checks for running processes.
  - **`profile_triggers`**: Modify this dictionary to customize which running applications will trigger a specific profile. You can add the process names of your favorite games or applications.

## Conclusion

This suite provides a powerful set of tools for anyone looking to get the most out of their network connection on Linux. Whether through manual fine-tuning or automated real-time adjustments, you can achieve a faster and more responsive network experience.
