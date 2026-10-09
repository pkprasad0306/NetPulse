"""
NetPulse - DNS Lookup Utility
Resolves hostnames to DNS records:
- A (IPv4) & AAAA (IPv6) via Python socket standard library
- MX (Mail Exchange) & CNAME (Canonical Name) via dnspython with safe fallbacks
"""

import ipaddress
import re
import socket
import time
from typing import Any, Dict, List, Optional


def is_valid_domain_or_ip(host: str) -> bool:
    """
    Validates domain name or IP string format to reject invalid inputs.
    """
    if not host or not isinstance(host, str):
        return False
    host = host.strip()
    if len(host) == 0 or len(host) > 255:
        return False

    # 1. Check valid IPv4 or IPv6
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass

    # 2. Check valid domain name or single-label hostname
    pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$|'
        r'^[a-zA-Z0-9_-]+$'
    )
    return bool(pattern.match(host))


def lookup_dns(
    host: str,
    query_types: Optional[List[str]] = None,
    timeout_sec: float = 3.0,
) -> Dict[str, Any]:
    """
    Performs DNS resolution on the specified hostname or IP address.

    Parameters:
        host: Domain name or IP address (e.g., 'google.com')
        query_types: List of record types to resolve ['A', 'AAAA', 'MX', 'CNAME'].
                     Defaults to all four types if None.
        timeout_sec: Maximum timeout in seconds for DNS queries.

    Returns:
        Dictionary with status, query_time_ms, records dictionary, canonical_name, and error.
    """
    cleaned_host = host.strip() if isinstance(host, str) else ""

    if not is_valid_domain_or_ip(cleaned_host):
        return {
            "success": False,
            "host": cleaned_host,
            "status": "Invalid Host",
            "query_time_ms": None,
            "canonical_name": None,
            "records": {"A": [], "AAAA": [], "MX": [], "CNAME": []},
            "error": f"Invalid hostname or IP address: '{cleaned_host}'",
        }

    if query_types is None:
        query_types = ["A", "AAAA", "MX", "CNAME"]
    else:
        query_types = [qt.upper() for qt in query_types]

    records: Dict[str, List[Any]] = {
        "A": [],
        "AAAA": [],
        "MX": [],
        "CNAME": [],
    }
    canonical_name: Optional[str] = None
    start_time = time.perf_counter()

    # 1. Resolve A (IPv4) & AAAA (IPv6) and Canonical Name using socket
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout_sec)

        if "A" in query_types:
            try:
                addr_info_v4 = socket.getaddrinfo(
                    cleaned_host, None, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_CANONNAME
                )
                for item in addr_info_v4:
                    ip = item[4][0]
                    if ip not in records["A"]:
                        records["A"].append(ip)
                    if not canonical_name and item[3]:
                        canonical_name = item[3]
            except (socket.gaierror, socket.herror, socket.timeout):
                pass

        if "AAAA" in query_types:
            try:
                addr_info_v6 = socket.getaddrinfo(
                    cleaned_host, None, socket.AF_INET6, socket.SOCK_STREAM
                )
                for item in addr_info_v6:
                    ip = item[4][0]
                    if ip not in records["AAAA"]:
                        records["AAAA"].append(ip)
            except (socket.gaierror, socket.herror, socket.timeout):
                pass

        socket.setdefaulttimeout(old_timeout)

    except Exception:
        pass

    # 2. Resolve MX and CNAME using dnspython
    try:
        import dns.resolver  # dnspython

        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout_sec

        if "MX" in query_types:
            try:
                mx_answers = resolver.resolve(cleaned_host, "MX")
                for rdata in mx_answers:
                    records["MX"].append({
                        "preference": int(rdata.preference),
                        "exchange": str(rdata.exchange).rstrip("."),
                    })
                # Sort MX by preference (lowest number = highest priority)
                records["MX"].sort(key=lambda x: x["preference"])
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.exception.DNSException):
                pass

        if "CNAME" in query_types:
            try:
                cname_answers = resolver.resolve(cleaned_host, "CNAME")
                for rdata in cname_answers:
                    cname_target = str(rdata.target).rstrip(".")
                    if cname_target not in records["CNAME"]:
                        records["CNAME"].append(cname_target)
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.exception.DNSException):
                pass

    except ImportError:
        pass
    except Exception:
        pass

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    has_any_record = any(len(records[k]) > 0 for k in records)

    if has_any_record:
        return {
            "success": True,
            "host": cleaned_host,
            "status": "Resolved",
            "query_time_ms": elapsed_ms,
            "canonical_name": canonical_name or cleaned_host,
            "records": records,
            "error": None,
        }
    else:
        return {
            "success": False,
            "host": cleaned_host,
            "status": "Resolution Failed",
            "query_time_ms": elapsed_ms,
            "canonical_name": None,
            "records": records,
            "error": f"No DNS records found for '{cleaned_host}'.",
        }
