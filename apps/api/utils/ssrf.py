import socket
import ipaddress
from urllib.parse import urlparse
from fastapi import HTTPException, status

BLOCKED_HOSTNAMES = {
    "localhost", "127.0.0.1", "::1", "0.0.0.0",
    "postgres", "redis", "api", "web", "worker", "scheduler", "reflow_postgres", "reflow_redis", "reflow_api", "reflow_web"
}

PRIVATE_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.169.254/32"), # Cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def validate_url_ssrf(url_str: str) -> str:
    """Validates that a URL target is safe from Server-Side Request Forgery (SSRF).
    Raises HTTPException(400) if the URL resolves to private or loopback networks.
    """
    if not url_str or not isinstance(url_str, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_URL", "message": "URL must be a valid non-empty string"}
        )

    parsed = urlparse(url_str)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_SCHEME", "message": "Only http and https schemes are permitted"}
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_HOSTNAME", "message": "URL must include a valid hostname"}
        )

    if hostname in BLOCKED_HOSTNAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SSRF_BLOCKED", "message": "Access to local or internal infrastructure hostnames is prohibited"}
        )

    try:
        ip = ipaddress.ip_address(hostname)
        for net in PRIVATE_IP_NETWORKS:
            if ip in net:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "SSRF_BLOCKED", "message": f"Access to private IP range ({ip}) is prohibited"}
                )
    except ValueError:
        # Not a raw IP address; resolve hostname DNS
        try:
            resolved_ips = socket.getaddrinfo(hostname, None)
            for res in resolved_ips:
                sock_ip_str = res[4][0]
                resolved_ip = ipaddress.ip_address(sock_ip_str)
                for net in PRIVATE_IP_NETWORKS:
                    if resolved_ip in net:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"error": "SSRF_BLOCKED", "message": "Target hostname resolves to a private IP range"}
                        )
        except socket.gaierror:
            # Domain cannot be resolved safely
            pass

    return url_str
