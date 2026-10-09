"""
Unit tests for core/dns_lookup.py
Tests DNS queries with socket and dnspython mocks.
"""

import socket
from unittest.mock import patch, MagicMock
import pytest

from core.dns_lookup import is_valid_domain_or_ip, lookup_dns


def test_is_valid_domain_or_ip():
    """Test validation of domain and IP input formats."""
    assert is_valid_domain_or_ip("example.com") is True
    assert is_valid_domain_or_ip("sub.domain.org") is True
    assert is_valid_domain_or_ip("192.168.1.1") is True
    assert is_valid_domain_or_ip("2001:db8::1") is True
    assert is_valid_domain_or_ip("::1") is True
    assert is_valid_domain_or_ip("localhost") is True

    assert is_valid_domain_or_ip("999.999.999.999") is False
    assert is_valid_domain_or_ip("") is False
    assert is_valid_domain_or_ip("   ") is False
    assert is_valid_domain_or_ip("bad domain with spaces") is False
    assert is_valid_domain_or_ip(None) is False


@patch("socket.getaddrinfo")
def test_lookup_dns_a_and_aaaa(mock_getaddrinfo):
    """Test A and AAAA resolution using mocked socket."""
    def fake_getaddrinfo(host, port, family, socktype, proto=0, flags=0):
        if family == socket.AF_INET:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "example.com", ("93.184.216.34", 0))]
        elif family == socket.AF_INET6:
            return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "example.com", ("2606:2800:220:1:248:1893:25c8:1946", 0, 0, 0))]
        return []

    mock_getaddrinfo.side_effect = fake_getaddrinfo

    result = lookup_dns("example.com", query_types=["A", "AAAA"])
    assert result["success"] is True
    assert result["status"] == "Resolved"
    assert "93.184.216.34" in result["records"]["A"]
    assert "2606:2800:220:1:248:1893:25c8:1946" in result["records"]["AAAA"]
    assert result["canonical_name"] == "example.com"
    assert result["error"] is None


@patch("socket.getaddrinfo")
@patch("dns.resolver.Resolver")
def test_lookup_dns_mx_and_cname(mock_resolver_class, mock_getaddrinfo):
    """Test MX and CNAME record queries using mocked dnspython."""
    mock_getaddrinfo.return_value = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "alias.example.com", ("93.184.216.34", 0))
    ]

    mock_resolver_inst = MagicMock()
    mock_resolver_class.return_value = mock_resolver_inst

    # Mock MX answer
    mock_mx_1 = MagicMock()
    mock_mx_1.preference = 10
    mock_mx_1.exchange = "mail.example.com."

    mock_mx_2 = MagicMock()
    mock_mx_2.preference = 20
    mock_mx_2.exchange = "backup.example.com."

    # Mock CNAME answer
    mock_cname = MagicMock()
    mock_cname.target = "target.example.com."

    def fake_resolve(host, rdtype):
        if rdtype == "MX":
            return [mock_mx_2, mock_mx_1]
        elif rdtype == "CNAME":
            return [mock_cname]
        return []

    mock_resolver_inst.resolve.side_effect = fake_resolve

    result = lookup_dns("alias.example.com", query_types=["A", "MX", "CNAME"])
    assert result["success"] is True
    assert len(result["records"]["MX"]) == 2
    # Verify MX records are sorted by lowest preference number first
    assert result["records"]["MX"][0]["preference"] == 10
    assert result["records"]["MX"][0]["exchange"] == "mail.example.com"
    assert result["records"]["MX"][1]["preference"] == 20
    assert "target.example.com" in result["records"]["CNAME"]


@patch("socket.getaddrinfo")
def test_lookup_dns_host_not_found(mock_getaddrinfo):
    """Test failed lookup for non-existent domain."""
    mock_getaddrinfo.side_effect = socket.gaierror(-2, "Name or service not known")

    result = lookup_dns("nonexistent-domain-12345abc.xyz", query_types=["A", "AAAA"])
    assert result["success"] is False
    assert result["status"] == "Resolution Failed"
    assert len(result["records"]["A"]) == 0
    assert result["error"] is not None


def test_lookup_dns_invalid_input():
    """Test lookup handling on invalid host format."""
    result = lookup_dns("bad input; injection")
    assert result["success"] is False
    assert result["status"] == "Invalid Host"
