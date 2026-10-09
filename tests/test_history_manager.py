"""
Unit tests for core/history_manager.py
Tests CSV file creation, logging, loading, clearing, and exporting.
"""

import os
import pandas as pd
import pytest

from core.history_manager import (
    log_diagnostic,
    load_history,
    clear_history,
    get_history_df,
    get_history_csv_bytes,
    ensure_data_directory,
)


def test_ensure_data_directory(tmp_path):
    """Test safe directory creation."""
    target_dir = tmp_path / "sub" / "data"
    target_file = target_dir / "test.csv"
    assert not target_dir.exists()

    ensure_data_directory(str(target_file))
    assert target_dir.exists()


def test_log_and_load_history(tmp_path):
    """Test logging records and loading them back accurately."""
    test_csv = str(tmp_path / "history.csv")

    # Load from non-existent file should return empty list
    assert load_history(test_csv) == []

    # Log 1st record
    success = log_diagnostic(
        tool="Ping",
        target="8.8.8.8",
        status="Reachable",
        latency_ms=14.5,
        details="0% packet loss",
        history_file=test_csv,
    )
    assert success is True

    # Log 2nd record
    success = log_diagnostic(
        tool="DNS Lookup",
        target="google.com",
        status="Resolved",
        latency_ms=12.2,
        details="Resolved: 142.250.190.46",
        history_file=test_csv,
    )
    assert success is True

    # Load history
    records = load_history(test_csv)
    assert len(records) == 2
    assert records[0]["tool"] == "Ping"
    assert records[0]["target"] == "8.8.8.8"
    assert records[0]["status"] == "Reachable"
    assert records[0]["latency_ms"] == 14.5

    assert records[1]["tool"] == "DNS Lookup"
    assert records[1]["target"] == "google.com"


def test_clear_history(tmp_path):
    """Test clearing all records while keeping CSV headers."""
    test_csv = str(tmp_path / "history.csv")

    log_diagnostic("Ping", "127.0.0.1", "Reachable", 1.0, history_file=test_csv)
    assert len(load_history(test_csv)) == 1

    cleared = clear_history(test_csv)
    assert cleared is True
    assert load_history(test_csv) == []


def test_get_history_df(tmp_path):
    """Test DataFrame conversion."""
    test_csv = str(tmp_path / "history.csv")

    # Empty
    empty_df = get_history_df(test_csv)
    assert isinstance(empty_df, pd.DataFrame)
    assert empty_df.empty

    # With rows
    log_diagnostic("TCP Port", "127.0.0.1:80", "Open", 2.3, history_file=test_csv)
    df = get_history_df(test_csv)
    assert len(df) == 1
    assert df.iloc[0]["tool"] == "TCP Port"


def test_get_history_csv_bytes(tmp_path):
    """Test binary CSV byte export."""
    test_csv = str(tmp_path / "history.csv")
    log_diagnostic("Ping", "8.8.8.8", "Reachable", 15.0, history_file=test_csv)

    csv_bytes = get_history_csv_bytes(test_csv)
    assert isinstance(csv_bytes, bytes)
    assert b"Ping" in csv_bytes
    assert b"8.8.8.8" in csv_bytes
