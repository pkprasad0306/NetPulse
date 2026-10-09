"""
NetPulse - Host Reachability (Ping) Checker
Executes platform-aware ICMP ping commands with strict timeouts,
safe subprocess execution (no shell=True), and input validation.
"""

import ipaddress
import platform
import re
import subprocess
from typing import Any, Dict, Optional


def is_valid_host(host: str) -> bool:
    """
    Validates whether the provided string is a plausible hostname or IP address.
    Prevents shell injection characters, spaces, and empty strings.
    """
    if not host or not isinstance(host, str):
        return False
    host = host.strip()
    if len(host) == 0 or len(host) > 255:
        return False

    # 1. Check if it is a valid IPv4 or IPv6 literal
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass

    # 2. Check if it is a valid Domain name or single-label hostname (e.g., localhost)
    hostname_pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$|'
        r'^[a-zA-Z0-9_-]+$'
    )
    return bool(hostname_pattern.match(host))


def parse_ping_output(output: str, is_windows: bool) -> Dict[str, Any]:
    """
    Parses ping command output to extract round-trip latency (ms) and packet loss percentage.
    """
    latency_ms: Optional[float] = None
    packet_loss: float = 100.0

    if is_windows:
        # Match Windows latency: 'Average = 14ms' or 'time=14ms' or 'time<1ms'
        avg_match = re.search(r'Average\s*=\s*(\d+)\s*ms', output, re.IGNORECASE)
        if avg_match:
            latency_ms = float(avg_match.group(1))
        else:
            time_match = re.search(r'time[=<]\s*(\d+)\s*ms', output, re.IGNORECASE)
            if time_match:
                latency_ms = float(time_match.group(1))

        # Match Windows packet loss: '(0% loss)'
        loss_match = re.search(r'\((\d+)%\s*loss\)', output, re.IGNORECASE)
        if loss_match:
            packet_loss = float(loss_match.group(1))
        elif latency_ms is not None:
            packet_loss = 0.0
    else:
        # Match Unix/Linux latency: 'min/avg/max/mdev = 12.345/14.567/...' or 'time=14.5 ms'
        rtt_match = re.search(r'(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*[\d.]+/([\d.]+)/', output, re.IGNORECASE)
        if rtt_match:
            latency_ms = float(rtt_match.group(1))
        else:
            time_match = re.search(r'time[=](\d+(?:\.\d+)?)\s*ms', output, re.IGNORECASE)
            if time_match:
                latency_ms = float(time_match.group(1))

        # Match Unix packet loss: '0% packet loss'
        loss_match = re.search(r'(\d+(?:\.\d+)?)%\s*packet\s*loss', output, re.IGNORECASE)
        if loss_match:
            packet_loss = float(loss_match.group(1))
        elif latency_ms is not None:
            packet_loss = 0.0

    return {
        "latency_ms": latency_ms,
        "packet_loss": packet_loss,
    }


def check_ping(
    host: str,
    count: int = 1,
    timeout_sec: int = 2,
) -> Dict[str, Any]:
    """
    Executes a ping check against a target host or IP.
    """
    cleaned_host = host.strip() if isinstance(host, str) else ""

    if not is_valid_host(cleaned_host):
        return {
            "success": False,
            "host": cleaned_host,
            "status": "Invalid Host",
            "latency_ms": None,
            "packet_loss": 100.0,
            "output": "",
            "error": f"Invalid hostname or IP address: '{cleaned_host}'",
        }

    is_windows = platform.system().lower() == "windows"

    # Construct platform-specific ping command
    if is_windows:
        cmd = ["ping", "-n", str(max(1, count)), "-w", str(timeout_sec * 1000), cleaned_host]
    else:
        cmd = ["ping", "-c", str(max(1, count)), "-W", str(timeout_sec), cleaned_host]

    process_timeout = (timeout_sec * count) + 3

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=process_timeout,
            shell=False,
        )

        raw_output = (result.stdout or "") + (result.stderr or "")
        parsed = parse_ping_output(raw_output, is_windows)

        if result.returncode == 0 and parsed["packet_loss"] < 100.0:
            status = "Reachable"
            success = True
        else:
            status = "Unreachable"
            success = False

        return {
            "success": success,
            "host": cleaned_host,
            "status": status,
            "latency_ms": parsed["latency_ms"],
            "packet_loss": parsed["packet_loss"],
            "output": raw_output.strip(),
            "error": None if success else "Host did not respond or packet was dropped.",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "host": cleaned_host,
            "status": "Timed Out",
            "latency_ms": None,
            "packet_loss": 100.0,
            "output": "",
            "error": f"Ping request timed out after {process_timeout} seconds.",
        }
    except Exception as exc:
        return {
            "success": False,
            "host": cleaned_host,
            "status": "Error",
            "latency_ms": None,
            "packet_loss": 100.0,
            "output": "",
            "error": f"Execution error: {str(exc)}",
        }
