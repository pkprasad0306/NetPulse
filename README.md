# 🖧 NetPulse — Network Diagnostics Toolkit

**NetPulse** is a clean, beginner-friendly Python project for essential network troubleshooting and connectivity diagnostics. It features a modern **Streamlit** dashboard, persistent **CSV history tracking**, **exportable reports**, and an automated **pytest** test suite.

---

## 🚀 Features

1. **🏓 Host Reachability (Ping)**:
   - Uses platform-aware ICMP ping commands (Windows `-n`, Linux/macOS `-c`).
   - Strict timeouts and safe subprocess execution (without `shell=True`).
   - Measures round-trip latency (ms) and packet loss percentage.

2. **🌐 DNS Record Lookup**:
   - Resolves IPv4 (`A`) and IPv6 (`AAAA`) addresses using standard library sockets.
   - Queries Mail Exchange (`MX`) and Canonical Name (`CNAME`) records using `dnspython`.
   - Computes query lookup latency in milliseconds.

3. **🔌 Single TCP Port Connectivity**:
   - Tests reachability for any individual TCP port (1–65535).
   - Fast socket connection timeouts with automatic service identification (e.g. HTTP, HTTPS, SSH, MySQL).

4. **📊 Diagnostic History & Export**:
   - Automatically records every test outcome with timestamps to `data/diagnostic_history.csv`.
   - Filter history by tool or status.
   - Download reports instantly in **CSV** or **JSON** format.

5. **🧪 Automated Tests**:
   - Comprehensive unit test suite with 100% offline mocking using `pytest`.

---

## 📁 Project Structure

```text
NetPulse/
│
├── core/                          # Modular diagnostic logic (independent of UI)
│   ├── __init__.py                # Package initializer
│   ├── ping_checker.py            # Ping host reachability checker
│   ├── dns_lookup.py              # DNS resolution (A, AAAA, MX, CNAME)
│   ├── port_scanner.py            # Single TCP port connectivity checker
│   └── history_manager.py         # CSV history logging, retrieval, and export
│
├── tests/                         # Pytest automated test suite
│   ├── __init__.py
│   ├── test_ping_checker.py       # Unit tests for ping checker
│   ├── test_dns_lookup.py         # Unit tests for DNS lookup
│   ├── test_port_scanner.py       # Unit tests for TCP port checker
│   └── test_history_manager.py    # Unit tests for CSV history manager
│
├── app.py                         # Streamlit web dashboard
├── requirements.txt               # Project dependencies
├── data/                          # Diagnostic logs directory
│   └── .gitkeep
└── README.md                      # Documentation & instructions
```

---

## ⚙️ Installation & Setup (Windows)

### 1. Open PowerShell in the project directory
```powershell
cd "c:\Users\PRASAD KASURDE\OneDrive\Desktop\NetPluse"
```

### 2. (Optional) Create and activate a virtual environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install required dependencies
```powershell
python -m pip install -r requirements.txt
```

---

## 🧪 Running Automated Tests

Run the full pytest suite with verbose output:
```powershell
python -m pytest tests/ -v
```

---

## 🌐 Launching the Streamlit Web Dashboard

Start the local web application:
```powershell
python -m streamlit run app.py
```

Once started, open your browser and navigate to:
```text
http://localhost:8501
```

---

## 🛡️ Design Principles & Safety

- **Safe Subprocess**: Subprocess arguments are passed as structured lists with `shell=False` and strict timeouts to prevent command injection.
- **Independent Core**: All business logic resides in `core/` and can be imported in other scripts or CLI tools without requiring Streamlit.
- **Offline-Friendly Tests**: Network calls in tests are fully mocked so unit tests never fail due to intermittent internet connectivity.
