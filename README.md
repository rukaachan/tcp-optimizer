
# TCP Optimizer for Linux

A Python-based utility designed to easily analyze and optimize TCP/IP settings on Linux systems for enhanced internet speed and network performance.

## ✨ Features

  * **Interactive TUI:** A user-friendly Terminal User Interface to guide you through optimization.
  * **Automatic Analysis:** Analyzes your current network speed to recommend and apply the best TCP profile.
  * **Pre-defined Profiles:** Choose from a list of profiles optimized for different scenarios (e.g., high throughput, low latency).
  * **Benchmarking:** Automatically runs a speed test before and after applying changes to measure the impact.
  * **Safe Revert:** Backs up your original settings and allows you to restore them with a single command.
  * **CLI Support:** Includes a command-line interface for automation and scripting.

## 🚀 How It Works

This tool tunes your system's network performance by adjusting kernel parameters (`sysctl`) based on proven configurations. Key parameters modified include:

  * **Congestion Control:** Implements modern algorithms like `BBR` or `Cubic`.
  * **Packet Queuing:** Sets efficient queueing disciplines like `FQ_CoDel`.
  * **Buffer Sizes:** Optimizes TCP receive/send memory buffers.
  * **And much more...** (e.g., `tcp_fastopen`, `tcp_low_latency`, `tcp_mtu_probing`).

## 🛠️ Quick Start

1.  **Clone the repository:**

    ```bash
    https://github.com/rukaachan/tcp-optimizer
    cd tcp-optimizer
    ```

2.  **Install dependencies:**

    ```bash
    pip install "speedtest-cli" "typer[all]" "pydantic"
    ```

3.  **Run the interactive optimizer:**

    ```bash
    python -m src.main
    ```

## Advanced Optimization

For maximum performance, this tool can be used alongside other external methods:

  * **NIC Tuning (`ethtool`):** Adjust network card parameters like ring buffers and hardware offloading.
  * **QoS (`tc`):** Implement traffic shaping rules to prioritize critical packets.
  * **System Profiles (`tuned`):** Use system-wide daemons like `tuned` with profiles such as `network-throughput`.
  * **Kernel Updates:** Regularly updating your kernel can introduce significant networking improvements.