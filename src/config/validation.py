from pydantic import BaseModel, ValidationError, Field
from typing import Dict, Any

class ProfileSettings(BaseModel):
    """
    Pydantic model for validating individual profile settings.
    """
    net_ipv4_tcp_congestion_control: str = Field(..., alias="net.ipv4.tcp_congestion_control")
    net_core_default_qdisc: str = Field(..., alias="net.core.default_qdisc")
    net_ipv4_tcp_mtu_probing: int = Field(..., alias="net.ipv4.tcp_mtu_probing")
    net_core_rmem_max: int = Field(..., alias="net.core.rmem_max")
    net_core_wmem_max: int = Field(..., alias="net.core.wmem_max")
    net_ipv4_tcp_rmem: str = Field(..., alias="net.ipv4.tcp_rmem")
    net_ipv4_tcp_wmem: str = Field(..., alias="net.ipv4.tcp_wmem")
    net_core_netdev_max_backlog: int = Field(..., alias="net.core.netdev_max_backlog")
    vm_min_free_kbytes: int = Field(..., alias="vm.min_free_kbytes")
    net_ipv4_tcp_low_latency: int = Field(..., alias="net.ipv4.tcp_low_latency")
    net_ipv4_tcp_autocorking: int = Field(..., alias="net.ipv4.tcp_autocorking")
    net_ipv4_tcp_fastopen: int = Field(..., alias="net.ipv4.tcp_fastopen")
    net_ipv4_tcp_no_metrics_save: int = Field(..., alias="net.ipv4.tcp_no_metrics_save")
    net_ipv4_tcp_window_scaling: int = Field(..., alias="net.ipv4.tcp_window_scaling")
    net_ipv4_tcp_sack: int = Field(..., alias="net.ipv4.tcp_sack")
    net_ipv4_tcp_timestamps: int = Field(..., alias="net.ipv4.tcp_timestamps")
    net_ipv4_tcp_fin_timeout: int = Field(..., alias="net.ipv4.tcp_fin_timeout")
    net_ipv4_tcp_tw_reuse: int = Field(..., alias="net.ipv4.tcp_tw_reuse")
    net_ipv4_tcp_syncookies: int = Field(..., alias="net.ipv4.tcp_syncookies")
    net_ipv4_tcp_max_syn_backlog: int = Field(..., alias="net.ipv4.tcp_max_syn_backlog")
    net_ipv4_tcp_slow_start_after_idle: int = Field(..., alias="net.ipv4.tcp_slow_start_after_idle")
    net_ipv4_tcp_notsent_lowat: int = Field(..., alias="net.ipv4.tcp_notsent_lowat")

class Profile(BaseModel):
    """
    Pydantic model for validating a single profile structure.
    """
    description: str
    settings: ProfileSettings

class ProfilesConfig(BaseModel):
    """
    Pydantic model for validating the entire profiles.json structure.
    """
    __root__: Dict[str, Profile]

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the loaded configuration against the ProfilesConfig schema.
    Raises ValidationError if validation fails.
    """
    try:
        validated_config = ProfilesConfig.parse_obj(config)
        return validated_config.dict(by_alias=True)
    except ValidationError as e:
        raise ValueError(f"Configuration validation error: {e}")