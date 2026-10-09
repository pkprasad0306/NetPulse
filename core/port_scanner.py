"""
NetPulse - TCP Port Connectivity Checker
Tests single-host, single-TCP-port reachability using Python socket.
"""

import errno
import ipaddress
import socket
import time
from typing import Any, Dict, Optional, Tuple

# Common TCP Port to Service Name mapping for helpful UI context
COMMON_SERVICES: Dict[int, str] = {
    20: "FTP-Data",
    21: "FTP",
    22: "SSH / SFTP",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP (Web)",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS (Secure Web)",
    465: "SMTPS",
    587: "SMTP Submission",
    993: "IMAPS",
    995: "POP3S",
    1433: "Microsoft SQL Server",
    1521: "Oracle DB",
    3306: "MySQL Database",
    3389: "RDP (Remote Desktop)",
    5432: "PostgreSQL Database",
    6379: "Redis",
    8000: "HTTP Dev / Alt",
    8080: "HTTP Alternate / Proxy",
    8443: "HTTPS Alternate",
    9000: "SonarQube / PHP-FPM",
    27017: "MongoDB",
}


def get_service_name(port: int) -> str:
    """
    Returns the recognized service name for a given port number.
    """
    if port in COMMON_SERVICES:
        return COMMON_SERVICES[port]
    try:
        return socket.getservbyport(port, "tcp").upper()
    except (OSError, socket.error):
        return "Unknown Service"


def validate_port_target(host: str, port: Any) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validates host and port inputs.
    Returns: (is_valid, parsed_port, error_message)
    """
    if not host or not isinstance(host, str) or len(host.strip()) == 0:
        return False, None, "Target host cannot be empty."

    try:
        port_num = int(port)
    except (ValueError, TypeError):
        return False, None, f"Port must be an integer (received: {port})."

    if port_num < 1 or port_num > 65535:
        return False, None, f"Port number must be between 1 and 65535 (received: {port_num})."

    return True, port_num, None


def check_port(
    host: str,
    port: int,
    timeout_sec: float = 2.0,
) -> Dict[str, Any]:
    """
    Checks connectivity to a single TCP port on a target host.

    Parameters:
        host: Target hostname or IP address (e.g. '127.0.0.1' or 'example.com')
        port: TCP port number (1 - 65535)
        timeout_sec: Connection timeout in seconds (default: 2.0)

    Returns:
        Dictionary containing:
        - success (bool): True if TCP connection succeeded (port is Open)
        - host (str): Target host
        - port (int): Target port
        - service (str): Common service name (e.g. 'HTTP (Web)')
        - status (str): 'Open', 'Closed', 'Timed Out', or 'Invalid Input'
        - response_time_ms (float | None): Time taken to establish connection in ms
        - error (str | None): Descriptive error message if unreachable
    """
    cleaned_host = host.strip() if isinstance(host, str) else ""
    is_valid, validated_port, validation_error = validate_port_target(cleaned_host, port)

    if not is_valid or validated_port is None:
        return {
            "success": False,
            "host": cleaned_host,
            "port": port if isinstance(port, int) else None,
            "service": "Unknown",
            "status": "Invalid Input",
            "response_time_ms": None,
            "error": validation_error,
        }

    service = get_service_name(validated_port)
    start_time = time.perf_counter()

    # Determine socket address family (IPv4 vs IPv6)
    address_family = socket.AF_INET
    try:
        ip_obj = ipaddress.ip_address(cleaned_host)
        if ip_obj.version == 6:
            address_family = socket.AF_INET6
    except ValueError:
        pass

    sock = socket.socket(address_family, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)

    try:
        result_code = sock.connect_ex((cleaned_host, validated_port))
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if result_code == 0:
            return {
                "success": True,
                "host": cleaned_host,
                "port": validated_port,
                "service": service,
                "status": "Open",
                "response_time_ms": elapsed_ms,
                "error": None,
            }
        elif result_code in (errno.ECONNREFUSED, 10061, 111):
            return {
                "success": False,
                "host": cleaned_host,
                "port": validated_port,
                "service": service,
                "status": "Closed",
                "response_time_ms": elapsed_ms,
                "error": "Connection refused (port is closed or service is not running).",
            }
        elif result_code in (errno.ETIMEDOUT, 10060, 110):
            return {
                "success": False,
                "host": cleaned_host,
                "port": validated_port,
                "service": service,
                "status": "Timed Out",
                "response_time_ms": None,
                "error": f"Connection timed out after {timeout_sec} seconds (firewalled or host down).",
            }
        else:
            return {
                "success": False,
                "host": cleaned_host,
                "port": validated_port,
                "service": service,
                "status": "Closed / Filtered",
                "response_time_ms": elapsed_ms,
                "error": f"Socket error code: {result_code}",
            }

    except socket.gaierror:
        return {
            "success": False,
            "host": cleaned_host,
            "port": validated_port,
            "service": service,
            "status": "Host Not Found",
            "response_time_ms": None,
            "error": f"Could not resolve host '{cleaned_host}'.",
        }
    except socket.timeout:
        return {
            "success": False,
            "host": cleaned_host,
            "port": validated_port,
            "service": service,
            "status": "Timed Out",
            "response_time_ms": None,
            "error": f"Connection timed out after {timeout_sec} seconds.",
        }
    except Exception as exc:
        return {
            "success": False,
            "host": cleaned_host,
            "port": validated_port,
            "service": service,
            "status": "Error",
            "response_time_ms": None,
            "error": f"Socket exception: {str(exc)}",
        }
    finally:
        sock.close()
