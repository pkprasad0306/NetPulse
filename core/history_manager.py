"""
NetPulse - Diagnostic History Manager
Handles persistent CSV logging, history retrieval, clearing, and CSV export.
Safely creates the data directory and CSV files on demand and handles missing/corrupt data.
"""

import csv
from datetime import datetime
import io
import os
from typing import Any, Dict, List, Optional
import pandas as pd

# Default history file path
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_HISTORY_FILE = os.path.join(DEFAULT_DATA_DIR, "diagnostic_history.csv")

CSV_HEADERS = ["timestamp", "tool", "target", "status", "latency_ms", "details"]


def ensure_data_directory(file_path: str) -> None:
    """
    Safely creates the parent directory of the file if it does not exist.
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def log_diagnostic(
    tool: str,
    target: str,
    status: str,
    latency_ms: Optional[float] = None,
    details: str = "",
    history_file: Optional[str] = None,
) -> bool:
    """
    Appends a new diagnostic result entry to the CSV history file.

    Parameters:
        tool: Diagnostic tool used (e.g. 'Ping', 'DNS Lookup', 'TCP Port')
        target: Target destination (e.g. 'google.com', '1.1.1.1:443')
        status: Result status (e.g. 'Reachable', 'Resolved', 'Open', 'Closed')
        latency_ms: Optional latency or response time in milliseconds
        details: Optional textual summary or record details
        history_file: Optional custom CSV file path (defaults to data/diagnostic_history.csv)

    Returns:
        bool: True if logged successfully, False otherwise.
    """
    file_path = history_file or DEFAULT_HISTORY_FILE

    try:
        ensure_data_directory(file_path)
        file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        latency_str = f"{latency_ms:.2f}" if latency_ms is not None else ""

        with open(file_path, mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": timestamp_str,
                "tool": str(tool).strip(),
                "target": str(target).strip(),
                "status": str(status).strip(),
                "latency_ms": latency_str,
                "details": str(details).replace("\n", " ").strip(),
            })
        return True
    except Exception:
        return False


def load_history(history_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Reads the history CSV file and returns a list of diagnostic record dictionaries.
    Gracefully handles missing, empty, or unreadable files.

    Returns:
        List of dictionaries with keys: timestamp, tool, target, status, latency_ms, details.
    """
    file_path = history_file or DEFAULT_HISTORY_FILE

    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return []

    records: List[Dict[str, Any]] = []
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if not row:
                    continue
                # Extract and sanitize row items
                latency_val = None
                raw_latency = row.get("latency_ms", "").strip()
                if raw_latency:
                    try:
                        latency_val = float(raw_latency)
                    except ValueError:
                        latency_val = None

                records.append({
                    "timestamp": row.get("timestamp", "").strip(),
                    "tool": row.get("tool", "").strip(),
                    "target": row.get("target", "").strip(),
                    "status": row.get("status", "").strip(),
                    "latency_ms": latency_val,
                    "details": row.get("details", "").strip(),
                })
    except Exception:
        return []

    return records


def clear_history(history_file: Optional[str] = None) -> bool:
    """
    Safely clears all diagnostic records from the CSV file.
    """
    file_path = history_file or DEFAULT_HISTORY_FILE

    try:
        ensure_data_directory(file_path)
        with open(file_path, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
            writer.writeheader()
        return True
    except Exception:
        return False


def get_history_df(history_file: Optional[str] = None) -> pd.DataFrame:
    """
    Loads diagnostic history and returns a pandas DataFrame.
    """
    records = load_history(history_file)
    if not records:
        return pd.DataFrame(columns=CSV_HEADERS)
    return pd.DataFrame(records)


def get_history_csv_bytes(history_file: Optional[str] = None) -> bytes:
    """
    Returns the history CSV data as UTF-8 bytes for file download buttons.
    """
    file_path = history_file or DEFAULT_HISTORY_FILE
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
        writer.writeheader()
        return output.getvalue().encode("utf-8")

    try:
        with open(file_path, mode="rb") as f:
            return f.read()
    except Exception:
        return b""
