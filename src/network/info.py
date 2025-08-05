import os
from src.utils.system import run_command
from src.network.sysctl import get_sysctl_value



def get_active_network_interface():
    """Determines the active network interface."""
    try:
        interface = run_command("ip route | grep default | awk '{print $5}'", suppress_errors=True, timeout=5).strip()
        if interface:
            return interface
        else:
            interfaces = run_command("ip -o link show | awk -F':' '{print $2}' | cut -d' ' -f2 | grep -v 'lo'", suppress_errors=True, timeout=5).splitlines()
    except Exception:
        pass
    return "N/A"

def get_system_information():
    """Gathers and returns key system information."""
    info = {}
    info["Kernel Version"] = run_command("uname -r", suppress_errors=True, timeout=5)
    os_name = ""
    os_name = run_command("lsb_release -d -s", suppress_errors=True, timeout=5)
    if "Error" in os_name or not os_name:
        os_name = run_command("""cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '"'""", suppress_errors=True, timeout=5)
        if "Error" in os_name or not os_name:
            os_name = run_command("head -n 1 /etc/issue", suppress_errors=True, timeout=5)
            if "Error" in os_name or not os_name:
                os_name = "Unknown Linux Distribution"
    info["Operating System"] = os_name.strip()
    info["Active Network Interface"] = get_active_network_interface()
    info["IP Address"] = run_command(f"ip -4 addr show {info['Active Network Interface']} | grep -oP '(?<=inet )[0-9.]+'", suppress_errors=True, timeout=5) if info["Active Network Interface"] else "N/A"
    info["Default Gateway"] = run_command("ip route | grep default | awk '{print $3}'", suppress_errors=True, timeout=5)
    info["DNS Servers"] = run_command("cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | paste -sd \",\" -", suppress_errors=True, timeout=5)

    # Add TCP/IP Kernel Parameters
    info["TCP Congestion Control"] = get_sysctl_value("net.ipv4.tcp_congestion_control")
    info["TCP Read Memory Max"] = get_sysctl_value("net.ipv4.tcp_rmem")
    info["TCP Write Memory Max"] = get_sysctl_value("net.ipv4.tcp_wmem")
    info["Default Qdisc"] = get_sysctl_value("net.core.default_qdisc")
    info["Netdev Max Backlog"] = get_sysctl_value("net.core.netdev_max_backlog")

    # Add Network Interface Statistics
    link_stats = run_command("ip -s link", suppress_errors=True, timeout=5)
    if link_stats and info["Active Network Interface"] != "N/A":
        interface_section = ""
        for line in link_stats.splitlines():
            if info["Active Network Interface"] + ":" in line:
                interface_section = link_stats.split(info["Active Network Interface"] + ":")[1]
                break
        if interface_section:
            rx_line = ""
            tx_line = ""
            for line in interface_section.splitlines():
                if "RX: bytes" in line:
                    rx_line = line
                elif "TX: bytes" in line:
                    tx_line = line
            
            if rx_line:
                rx_parts = rx_line.split()
                info["RX Errors"] = rx_parts[3] if len(rx_parts) > 3 else "N/A"
                info["RX Dropped"] = rx_parts[4] if len(rx_parts) > 4 else "N/A"
            if tx_line:
                tx_parts = tx_line.split()
                info["TX Errors"] = tx_parts[3] if len(tx_parts) > 3 else "N/A"
                info["TX Dropped"] = tx_parts[4] if len(tx_parts) > 4 else "N/A"

    # Add Active TCP Connections Summary
    ss_output = run_command("ss -tuna", suppress_errors=True, timeout=5)
    if ss_output:
        estab_count = ss_output.count("ESTAB")
        listen_count = ss_output.count("LISTEN")
        time_wait_count = ss_output.count("TIME-WAIT")
        info["TCP Established"] = str(estab_count)
        info["TCP Listening"] = str(listen_count)
        info["TCP Time-Wait"] = str(time_wait_count)

    return info