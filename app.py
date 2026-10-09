"""
NetPulse — Network Diagnostics Toolkit
A beginner-friendly Streamlit web dashboard for network troubleshooting.
"""

import json
from datetime import datetime
import pandas as pd
import streamlit as st

from core.ping_checker import check_ping
from core.dns_lookup import lookup_dns
from core.port_scanner import check_port, COMMON_SERVICES
from core.history_manager import (
    log_diagnostic,
    load_history,
    clear_history,
    get_history_df,
    get_history_csv_bytes,
)

# Page configuration
st.set_page_config(
    page_title="NetPulse — Network Diagnostics Toolkit",
    page_icon="🖧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for polished UI
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #555555;
        margin-bottom: 1.2rem;
    }
    .card-box {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #e9ecef;
        margin-bottom: 10px;
    }
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-tool {
        background-color: #E3F2FD;
        color: #1565C0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def set_preset_target(target: str):
    """Callback to update preset host target across tabs."""
    st.session_state["preset_target"] = target


def set_preset_port(port_num: int):
    """Callback to update port number safely before widget instantiation."""
    st.session_state["port_input"] = port_num


def render_sidebar():
    """Renders the sidebar with quick presets and app details."""
    st.sidebar.title("🖧 NetPulse Toolkit")
    st.sidebar.caption("Simple & modular network diagnostics")

    st.sidebar.markdown("---")
    st.sidebar.subheader("💡 Quick Host Presets")
    col1, col2 = st.sidebar.columns(2)
    col1.button("Google DNS", on_click=set_preset_target, args=("8.8.8.8",), width="stretch")
    col2.button("Cloudflare", on_click=set_preset_target, args=("1.1.1.1",), width="stretch")
    col1.button("google.com", on_click=set_preset_target, args=("google.com",), width="stretch")
    col2.button("Localhost", on_click=set_preset_target, args=("127.0.0.1",), width="stretch")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Diagnostic Summary")
    history = load_history()
    st.sidebar.metric("Total Tests Logged", len(history))

    if len(history) > 0:
        latest = history[-1]
        st.sidebar.caption(f"Last test: **{latest['tool']}** ({latest['target']}) at `{latest['timestamp']}`")

    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Diagnostic History", type="secondary", width="stretch"):
        clear_history()
        st.sidebar.success("History cleared!")
        st.rerun()


def render_ping_tab():
    """Renders the Ping Reachability check interface."""
    st.header("🏓 Host Reachability (Ping)")
    st.write("Send ICMP echo requests to verify if a remote host or IP is reachable and measure round-trip latency.")

    default_host = st.session_state.get("preset_target", "8.8.8.8")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        target_host = st.text_input("Target Hostname or IP Address", value=default_host, key="ping_host_input")
    with col2:
        count = st.number_input("Packet Count", min_value=1, max_value=4, value=2, step=1, key="ping_count_input")
    with col3:
        timeout = st.number_input("Timeout (sec)", min_value=1, max_value=10, value=2, step=1, key="ping_timeout_input")

    if st.button("🚀 Run Ping Test", type="primary", key="ping_run_btn"):
        with st.spinner(f"Pinging {target_host}..."):
            result = check_ping(target_host, count=int(count), timeout_sec=int(timeout))

        # Log to persistent history
        details = f"Packet Loss: {result['packet_loss']:.0f}%"
        if result["error"]:
            details += f" | {result['error']}"
        log_diagnostic(
            tool="Ping",
            target=result["host"] or target_host,
            status=result["status"],
            latency_ms=result["latency_ms"],
            details=details,
        )

        st.markdown("---")
        st.subheader("Results")

        m1, m2, m3 = st.columns(3)
        with m1:
            if result["success"]:
                st.metric("Status", f"🟢 {result['status']}")
            else:
                st.metric("Status", f"🔴 {result['status']}")

        with m2:
            latency_display = f"{result['latency_ms']:.1f} ms" if result["latency_ms"] is not None else "N/A"
            st.metric("Round-Trip Latency", latency_display)

        with m3:
            st.metric("Packet Loss", f"{result['packet_loss']:.0f}%")

        if result["error"]:
            st.error(f"⚠️ {result['error']}")
        elif result["success"]:
            st.success(f"Host `{result['host']}` is reachable with {result['latency_ms']:.1f} ms latency.")

        with st.expander("📋 View Raw Ping Output"):
            st.code(result["output"] or "No raw output returned.", language="text")


def render_dns_tab():
    """Renders the DNS Lookup interface."""
    st.header("🌐 DNS Record Lookup")
    st.write("Query DNS records (A, AAAA, MX, CNAME) to inspect hostname resolution and IP mappings.")

    default_host = st.session_state.get("preset_target", "google.com")
    col1, col2 = st.columns([3, 1])
    with col1:
        target_domain = st.text_input("Target Domain / Hostname", value=default_host, key="dns_host_input")
    with col2:
        record_filter = st.multiselect(
            "Record Types",
            options=["A", "AAAA", "MX", "CNAME"],
            default=["A", "AAAA", "MX", "CNAME"],
            key="dns_records_filter",
        )

    if st.button("🔍 Resolve DNS", type="primary", key="dns_run_btn"):
        with st.spinner(f"Resolving DNS for {target_domain}..."):
            result = lookup_dns(target_domain, query_types=record_filter)

        # Summarize details for history
        resolved_ips = result["records"]["A"] + result["records"]["AAAA"]
        details = f"Resolved: {', '.join(resolved_ips[:3])}" if resolved_ips else (result["error"] or "No records")
        log_diagnostic(
            tool="DNS Lookup",
            target=result["host"] or target_domain,
            status=result["status"],
            latency_ms=result["query_time_ms"],
            details=details,
        )

        st.markdown("---")
        st.subheader("Resolution Results")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Status", "🟢 Resolved" if result["success"] else "🔴 Failed")
        with m2:
            st.metric("Query Time", f"{result['query_time_ms']} ms" if result["query_time_ms"] is not None else "N/A")
        with m3:
            st.metric("Canonical Name", result["canonical_name"] or "N/A")

        if result["error"]:
            st.error(f"⚠️ {result['error']}")
        elif result["success"]:
            st.success(f"Successfully resolved DNS records for `{result['host']}`.")

        if result["success"]:
            # Display A & AAAA records
            rec_col1, rec_col2 = st.columns(2)
            with rec_col1:
                st.markdown("##### 📌 IPv4 Addresses (A Records)")
                if result["records"]["A"]:
                    for ip in result["records"]["A"]:
                        st.info(f"**IPv4:** `{ip}`")
                else:
                    st.write("None found.")

            with rec_col2:
                st.markdown("##### 📌 IPv6 Addresses (AAAA Records)")
                if result["records"]["AAAA"]:
                    for ip in result["records"]["AAAA"]:
                        st.info(f"**IPv6:** `{ip}`")
                else:
                    st.write("None found.")

            # Display MX & CNAME records
            rec_col3, rec_col4 = st.columns(2)
            with rec_col3:
                st.markdown("##### ✉️ Mail Servers (MX Records)")
                if result["records"]["MX"]:
                    mx_df = pd.DataFrame(result["records"]["MX"])
                    st.dataframe(mx_df, width="stretch", hide_index=True)
                else:
                    st.write("None found.")

            with rec_col4:
                st.markdown("##### 🔗 Aliases (CNAME Records)")
                if result["records"]["CNAME"]:
                    for cname in result["records"]["CNAME"]:
                        st.info(f"**Alias for:** `{cname}`")
                else:
                    st.write("None found.")


def render_port_tab():
    """Renders the Single TCP Port connectivity test interface."""
    st.header("🔌 TCP Port Connectivity Checker")
    st.write("Test connectivity to a single TCP port on a target host to check if a service is actively listening.")

    default_host = st.session_state.get("preset_target", "google.com")

    # Initialize port_input in session_state before widget rendering if absent
    if "port_input" not in st.session_state:
        st.session_state["port_input"] = 443

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        target_host = st.text_input("Target Host or IP", value=default_host, key="port_host_input")
    with col2:
        port = st.number_input("TCP Port (1 - 65535)", min_value=1, max_value=65535, step=1, key="port_input")
    with col3:
        timeout = st.number_input("Timeout (sec)", min_value=1.0, max_value=10.0, value=2.0, step=0.5, key="port_timeout_input")

    # Common Port Buttons using on_click callbacks to prevent post-instantiation mutation
    st.markdown("##### Quick Port Presets:")
    p_col1, p_col2, p_col3, p_col4, p_col5, p_col6 = st.columns(6)
    p_col1.button("80 (HTTP)", on_click=set_preset_port, args=(80,), width="stretch")
    p_col2.button("443 (HTTPS)", on_click=set_preset_port, args=(443,), width="stretch")
    p_col3.button("22 (SSH)", on_click=set_preset_port, args=(22,), width="stretch")
    p_col4.button("53 (DNS)", on_click=set_preset_port, args=(53,), width="stretch")
    p_col5.button("3306 (MySQL)", on_click=set_preset_port, args=(3306,), width="stretch")
    p_col6.button("8080 (Alt-Web)", on_click=set_preset_port, args=(8080,), width="stretch")

    if st.button("⚡ Test Port Connectivity", type="primary", key="port_run_btn"):
        with st.spinner(f"Testing connection to {target_host}:{port}..."):
            result = check_port(target_host, port=int(port), timeout_sec=float(timeout))

        # Log to history
        details = f"Service: {result['service']}"
        if result["error"]:
            details += f" | {result['error']}"
        log_diagnostic(
            tool="TCP Port",
            target=f"{result['host'] or target_host}:{result['port'] or port}",
            status=result["status"],
            latency_ms=result["response_time_ms"],
            details=details,
        )

        st.markdown("---")
        st.subheader("Port Connectivity Result")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            if result["status"] == "Open":
                st.metric("Port Status", "🟢 OPEN")
            elif result["status"] == "Closed":
                st.metric("Port Status", "🔴 CLOSED")
            else:
                st.metric("Port Status", f"🟠 {result['status'].upper()}")

        with m2:
            st.metric("Target Port", f"{result['port']}")

        with m3:
            st.metric("Service", result["service"])

        with m4:
            resp_time = f"{result['response_time_ms']:.1f} ms" if result["response_time_ms"] is not None else "N/A"
            st.metric("Response Time", resp_time)

        if result["status"] == "Open":
            st.success(f"Port {result['port']} ({result['service']}) on `{result['host']}` is OPEN and accepting connections.")
        else:
            st.warning(f"Port {result['port']} ({result['service']}) on `{result['host']}` is {result['status']}. Reason: {result['error']}")


def render_history_tab():
    """Renders the diagnostic history table, summary metrics, and CSV/JSON export."""
    st.header("📊 Diagnostic History & Reports")
    st.write("Review all diagnostic tests executed during your sessions and export them as reports.")

    df = get_history_df()

    if df.empty:
        st.info("No diagnostic records logged yet. Run a Ping, DNS, or Port check to start recording data.")
        return

    # Metrics Summary
    total_tests = len(df)
    success_count = int(df["status"].isin(["Reachable", "Resolved", "Open"]).sum())
    success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0
    unique_tools = sorted(list(df["tool"].unique()))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tests", total_tests)
    col2.metric("Success Rate", f"{success_rate:.0f}%", f"{success_count}/{total_tests} passed")
    col3.metric("Tools Active", f"{len(unique_tools)} of 3", help=f"Tools used: {', '.join(unique_tools)}")

    # Calculate average latency for successful tests with valid latency
    valid_latencies = df[df["latency_ms"].notna()]["latency_ms"]
    avg_latency = valid_latencies.mean() if not valid_latencies.empty else None
    col4.metric("Avg Latency", f"{avg_latency:.1f} ms" if avg_latency is not None else "N/A")

    # Display clean tags for tools used
    tools_html = " ".join([f"<span class='badge badge-tool'>{t}</span>" for t in unique_tools])
    st.markdown(f"**Tools used in this history session:** {tools_html}", unsafe_allow_html=True)

    st.markdown("---")

    # Filters
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        selected_tool = st.selectbox("Filter by Tool", options=["All"] + sorted(list(df["tool"].unique())))
    with f_col2:
        selected_status = st.selectbox("Filter by Status", options=["All"] + sorted(list(df["status"].unique())))

    filtered_df = df.copy()
    if selected_tool != "All":
        filtered_df = filtered_df[filtered_df["tool"] == selected_tool]
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    st.caption(f"Showing **{len(filtered_df)}** of **{total_tests}** records")

    # Show table
    st.dataframe(
        filtered_df,
        width="stretch",
        hide_index=True,
    )

    st.markdown("---")
    st.subheader("📥 Export Diagnostic Report")

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        csv_bytes = get_history_csv_bytes()
        st.download_button(
            label="📄 Download Report as CSV",
            data=csv_bytes,
            file_name=f"netpulse_diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width="stretch",
        )

    with d_col2:
        json_str = df.to_json(orient="records", indent=2)
        st.download_button(
            label="📦 Download Report as JSON",
            data=json_str,
            file_name=f"netpulse_diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width="stretch",
        )


def main():
    """Main application layout."""
    render_sidebar()

    st.markdown('<div class="main-header">🖧 NetPulse — Network Diagnostics Toolkit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">A beginner-friendly diagnostic dashboard for network reachability, DNS lookups, and TCP port checks.</div>', unsafe_allow_html=True)

    tab_ping, tab_dns, tab_port, tab_history = st.tabs([
        "🏓 Ping Reachability",
        "🌐 DNS Lookup",
        "🔌 TCP Port Check",
        "📊 Diagnostic History & Export",
    ])

    with tab_ping:
        render_ping_tab()

    with tab_dns:
        render_dns_tab()

    with tab_port:
        render_port_tab()

    with tab_history:
        render_history_tab()


if __name__ == "__main__":
    main()
