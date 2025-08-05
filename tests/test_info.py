import pytest
from unittest.mock import patch
from src.network.info import get_system_information

@pytest.fixture
def mock_run_command():
    with patch('src.network.info.run_command') as mock:
        yield mock


    @patch('src.network.info.run_command')
    def test_get_system_information_success(self, mock_run_command):
        mock_run_command.side_effect = [
            "5.15.0-76-generic",  # uname -r
            "Ubuntu 22.04.3 LTS",  # lsb_release -d -s
            "eth0",  # ip route
            "192.168.1.100",  # ip -4 addr
            "nameserver 8.8.8.8",  # cat /etc/resolv.conf
            "192.168.1.1",  # ip route default gateway
            "net.ipv4.tcp_congestion_control = cubic", # get_sysctl_value
            "net.ipv4.tcp_rmem = 4096 131072 6291456", # get_sysctl_value
            "net.ipv4.tcp_wmem = 4096 16384 4194304", # get_sysctl_value
            "net.core.default_qdisc = fq_codel", # get_sysctl_value
            "net.core.netdev_max_backlog = 1000", # get_sysctl_value
            """2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000
    link/ether 00:0c:29:ab:cd:ef brd ff:ff:ff:ff:ff:ff
    altname enp0s3
    RX: bytes  packets  errors  dropped  overruns  frame
           10000      100      0        0         0     0
    TX: bytes  packets  errors  dropped  carrier  collisions
           20000      200      0        0         0        0""", # ip -s link
            """State       Recv-Q Send-Q Local Address:Port                Peer Address:Port
ESTAB       0      0 192.168.1.100:41712             1.1.1.1:https
ESTAB       0      0 192.168.1.100:36224            1.2.3.4:http
LISTEN      0      0 0.0.0.0:22                     0.0.0.0:*
TIME-WAIT   0      0 192.168.1.100:443              1.2.3.4:80""", # ss -tuna
        ]
        
        info = get_system_information()
        
        assert info["Kernel Version"] == "5.15.0-76-generic"
        assert info["Operating System"] == "Ubuntu 22.04.3 LTS"
        assert info["Active Network Interface"] == "eth0"
        assert info["IP Address"] == "192.168.1.100"
        assert info["Default Gateway"] == "192.168.1.1"
        assert info["DNS Servers"] == "8.8.8.8"
        assert info["TCP Congestion Control"] == "cubic"
        assert info["TCP Read Memory Max"] == "4096 131072 6291456"
        assert info["TCP Write Memory Max"] == "4096 16384 4194304"
        assert info["Default Qdisc"] == "fq_codel"
        assert info["Netdev Max Backlog"] == "1000"
        assert info["RX Errors"] == "0"
        assert info["RX Dropped"] == "0"
        assert info["TX Errors"] == "0"
        assert info["TX Dropped"] == "0"
        assert info["TCP Established"] == "2"
        assert info["TCP Listening"] == "1"
        assert info["TCP Time-Wait"] == "1"

    @patch('src.network.info.run_command', return_value="")
    def test_get_system_information_empty_commands(self, mock_run_command):
        info = get_system_information()
        assert info["Kernel Version"] == ""
        assert info["Operating System"] == "Unknown Linux Distribution"
        assert info["Active Network Interface"] == "N/A"
        assert info["IP Address"] == "N/A"
        assert info["Default Gateway"] == ""
        assert info["DNS Servers"] == ""
        assert info["TCP Congestion Control"] == "N/A"
        assert info["TCP Read Memory Max"] == "N/A"
        assert info["TCP Write Memory Max"] == "N/A"
        assert info["Default Qdisc"] == "N/A"
        assert info["Netdev Max Backlog"] == "N/A"
        assert "RX Errors" not in info
        assert "RX Dropped" not in info
        assert "TX Errors" not in info
        assert "TX Dropped" not in info
        assert info["TCP Established"] == "0"
        assert info["TCP Listening"] == "0"
        assert info["TCP Time-Wait"] == "0"