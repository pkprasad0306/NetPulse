"""
Unit tests for core/ping_checker.py
Tests host validation, output parsing, and subprocess execution with mocks.
"""

import subprocess
from unittest.mock import patch, MagicMock
import pytest

from core.ping_checker import is_valid_host, parse_ping_output, check_ping


def test_is_valid_host():
    """Verify that hostname and IP validation works accurately."""
    # Valid targets
    assert is_valid_host("google.com") is True
    assert is_valid_host("8.8.8.8") is True
    assert is_valid_host("127.0.0.1") is True
    assert is_valid_host("localhost") is True
    assert is_valid_host("sub.domain-name.co.uk") is True
    assert is_valid_host("::1") is True
    assert is_valid_host("2001:db8::1") is True

    # Invalid targets (out of range, injection, spaces, invalid chars)
    assert is_valid_host("999.999.999.999") is False
    assert is_valid_host("") is False
    assert is_valid_host("   ") is False
    assert is_valid_host("google.com; rm -rf /") is False
    assert is_valid_host("google.com | dir") is False
    assert is_valid_host("8.8.8.8 & calc") is False
    assert is_valid_host("bad host name") is False
    assert is_valid_host(None) is False


def test_parse_ping_output_windows():
    """Test parsing of Windows ping command outputs."""
    sample_win = """
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=14ms TTL=117
Reply from 8.8.8.8: bytes=32 time=15ms TTL=117

Ping statistics for 8.8.8.8:
    Packets: Sent = 2, Received = 2, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 14ms, Maximum = 15ms, Average = 14ms
"""
    parsed = parse_ping_output(sample_win, is_windows=True)
    assert parsed["latency_ms"] == 14.0
    assert parsed["packet_loss"] == 0.0


def test_parse_ping_output_unix():
    """Test parsing of Unix/Linux ping command outputs."""
    sample_unix = """
PING google.com (142.250.190.46) 56(84) bytes of data.
64 bytes from lga34s36-in-f14.1e100.net (142.250.190.46): icmp_seq=1 ttl=116 time=12.4 ms

--- google.com ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 12.412/12.412/12.412/0.000 ms
"""
    parsed = parse_ping_output(sample_unix, is_windows=False)
    assert parsed["latency_ms"] == 12.412
    assert parsed["packet_loss"] == 0.0


@patch("subprocess.run")
def test_check_ping_success(mock_run):
    """Test successful ping execution with mocked subprocess."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Reply from 8.8.8.8: bytes=32 time=18ms TTL=117\nAverage = 18ms (0% loss)",
        stderr="",
    )

    result = check_ping("8.8.8.8", count=1, timeout_sec=2)
    assert result["success"] is True
    assert result["status"] == "Reachable"
    assert result["host"] == "8.8.8.8"
    assert result["latency_ms"] == 18.0
    assert result["packet_loss"] == 0.0
    assert result["error"] is None


@patch("subprocess.run")
def test_check_ping_unreachable(mock_run):
    """Test unreachable ping execution with mocked subprocess."""
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="Request timed out.\nPackets: Sent = 1, Received = 0, Lost = 1 (100% loss)",
        stderr="",
    )

    result = check_ping("192.0.2.1", count=1, timeout_sec=1)
    assert result["success"] is False
    assert result["status"] == "Unreachable"
    assert result["packet_loss"] == 100.0
    assert result["error"] is not None


@patch("subprocess.run")
def test_check_ping_timeout(mock_run):
    """Test ping timeout exception handling."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="ping", timeout=5)

    result = check_ping("10.255.255.1", count=1, timeout_sec=2)
    assert result["success"] is False
    assert result["status"] == "Timed Out"
    assert "timed out" in result["error"].lower()


def test_check_ping_invalid_host():
    """Test ping handling when given an invalid host string."""
    result = check_ping("invalid; host --dangerous")
    assert result["success"] is False
    assert result["status"] == "Invalid Host"
    assert "Invalid hostname" in result["error"]
