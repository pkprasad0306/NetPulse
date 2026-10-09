"""
Unit tests for core/port_scanner.py
Tests single-host, single-TCP-port connectivity checks with socket mocks.
"""

import errno
import socket
from unittest.mock import patch, MagicMock
import pytest

from core.port_scanner import (
    get_service_name,
    validate_port_target,
    check_port,
)


def test_validate_port_target():
    """Test host and port input validation."""
    # Valid
    valid, port, err = validate_port_target("127.0.0.1", 80)
    assert valid is True
    assert port == 80
    assert err is None

    valid, port, err = validate_port_target("example.com", "443")
    assert valid is True
    assert port == 443

    # Invalid Port Numbers
    valid, port, err = validate_port_target("localhost", 0)
    assert valid is False
    assert "between 1 and 65535" in err

    valid, port, err = validate_port_target("localhost", 70000)
    assert valid is False

    valid, port, err = validate_port_target("localhost", "not_a_port")
    assert valid is False
    assert "must be an integer" in err

    # Invalid Host
    valid, port, err = validate_port_target("", 80)
    assert valid is False
    assert "cannot be empty" in err


def test_get_service_name():
    """Test mapping of port numbers to service names."""
    assert "HTTP" in get_service_name(80)
    assert "HTTPS" in get_service_name(443)
    assert "SSH" in get_service_name(22)
    assert "MySQL" in get_service_name(3306)


@patch("socket.socket")
def test_check_port_open(mock_socket_class):
    """Test TCP port open scenario."""
    mock_sock = MagicMock()
    mock_sock.connect_ex.return_value = 0  # 0 indicates success
    mock_socket_class.return_value = mock_sock

    result = check_port("127.0.0.1", port=80, timeout_sec=1.0)
    assert result["success"] is True
    assert result["status"] == "Open"
    assert result["port"] == 80
    assert result["response_time_ms"] is not None
    assert result["error"] is None


@patch("socket.socket")
def test_check_port_ipv6(mock_socket_class):
    """Test TCP port open scenario with IPv6 address."""
    mock_sock = MagicMock()
    mock_sock.connect_ex.return_value = 0
    mock_socket_class.return_value = mock_sock

    result = check_port("::1", port=80, timeout_sec=1.0)
    assert result["success"] is True
    assert result["status"] == "Open"
    mock_socket_class.assert_called_with(socket.AF_INET6, socket.SOCK_STREAM)


@patch("socket.socket")
def test_check_port_closed(mock_socket_class):
    """Test TCP port closed scenario (connection refused)."""
    mock_sock = MagicMock()
    mock_sock.connect_ex.return_value = errno.ECONNREFUSED
    mock_socket_class.return_value = mock_sock

    result = check_port("127.0.0.1", port=9999, timeout_sec=1.0)
    assert result["success"] is False
    assert result["status"] == "Closed"
    assert "refused" in result["error"].lower()


@patch("socket.socket")
def test_check_port_timeout(mock_socket_class):
    """Test TCP port timed out scenario."""
    mock_sock = MagicMock()
    mock_sock.connect_ex.side_effect = socket.timeout("timed out")
    mock_socket_class.return_value = mock_sock

    result = check_port("192.0.2.1", port=443, timeout_sec=1.0)
    assert result["success"] is False
    assert result["status"] == "Timed Out"
    assert "timed out" in result["error"].lower()


def test_check_port_invalid_args():
    """Test port check with invalid arguments."""
    result = check_port("localhost", port=99999)
    assert result["success"] is False
    assert result["status"] == "Invalid Input"
