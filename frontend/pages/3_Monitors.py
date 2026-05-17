"""Monitors - Monitor control center"""
import streamlit as st
from api_client import BrandIntelAPI
from utils.formatters import format_datetime, format_relative_time

st.set_page_config(page_title="Monitors", page_icon=":satellite_antenna:", layout="wide")

@st.cache_resource
def get_api():
    return BrandIntelAPI()

api = get_api()

st.title(":satellite_antenna: Monitor Control Center")

# Fetch data
monitor_status = api.get_monitor_status()
brands = api.list_brands(active_only=True)

if not monitor_status or "error" in monitor_status:
    st.error("Failed to fetch monitor status")
    st.stop()

# Manual trigger section
with st.expander("Manual Trigger", expanded=True):
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        brand_options = {"All Active Brands": None}
        if brands and isinstance(brands, list):
            for b in brands:
                brand_options[b["name"]] = b["id"]
        selected_brand = st.selectbox("Select Brand", list(brand_options.keys()))
    
    with col2:
        if st.button("Trigger All Monitors", type="primary", use_container_width=True):
            brand_id = brand_options.get(selected_brand)
            with st.spinner("Triggering monitors..."):
                result = api.trigger_all_monitors(brand_id)
            if result and "error" not in result:
                st.success(
                    f"Scan complete: {result.get('total_hits_found', 0)} hits found, "
                    f"{result.get('total_hits_stored', 0)} stored, "
                    f"{result.get('total_hits_enriched', 0)} enriched"
                )
                st.rerun()
            else:
                st.error(f"Trigger failed: {result}")
    
    with col3:
        if st.button("Refresh Status", use_container_width=True):
            st.rerun()

st.divider()

# Monitor status grid
st.subheader("Monitor Status")
monitors = monitor_status.get("monitors", [])
cols = st.columns(min(len(monitors), 4))

for i, monitor in enumerate(monitors):
    with cols[i % len(cols)]:
        status = monitor.get("status", "unknown")
        status_icon = {
            "healthy": ":green_circle:",
            "degraded": ":orange_circle:", 
            "unhealthy": ":red_circle:"
        }.get(status, ":gray_circle:")
        
        with st.container(border=True):
            st.markdown(f"{status_icon} **{monitor.get('name', 'Unknown')}**")
            st.metric("Success Rate", f"{monitor.get('success_rate', 0) * 100:.1f}%")
            st.metric("Avg Time", f"{monitor.get('avg_execution_time', 0):.2f}s")
            
            last_run = monitor.get("last_run")
            if last_run:
                st.caption(f"Last: {format_relative_time(last_run)}")
            
            # Trigger button for specific monitor
            monitor_type = monitor.get("type", "")
            if selected_brand and brand_options.get(selected_brand):
                if st.button(f"Trigger {monitor.get('name')}", key=f"trigger_{monitor_type}", type="secondary"):
                    with st.spinner(f"Triggering {monitor.get('name')}..."):
                        result = api.trigger_monitor(monitor_type, brand_options[selected_brand])
                    if result and "error" not in result:
                        st.success(
                            f"Found {result.get('hits_found', 0)} hits, "
                            f"{result.get('hits_stored', 0)} stored, "
                            f"{result.get('hits_enriched', 0)} enriched"
                        )
                    else:
                        st.error(f"Trigger failed")

st.divider()

# Circuit breaker status
st.subheader("Circuit Breaker Status")
cb_states = monitor_status.get("circuit_breaker", {})
if cb_states:
    for monitor_type, state in cb_states.items():
        state_val = state.get("state", "closed")
        state_color = {"closed": "green", "open": "red", "half_open": "orange"}.get(state_val, "gray")
        
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.markdown(f":{state_color}[{state_val.upper()}] **{monitor_type}**")
        with col2:
            st.caption(f"Failures: {state.get('failure_count', 0)}")
        with col3:
            last_failure = state.get("last_failure")
            st.caption(f"Last: {format_datetime(last_failure) if last_failure else 'N/A'}")
        with col4:
            if state_val == "open":
                if st.button("Reset", key=f"cb_reset_{monitor_type}"):
                    api.reset_circuit_breaker(monitor_type)
                    st.success(f"Circuit breaker reset for {monitor_type}")
else:
    st.info("No circuit breaker data")

st.divider()

# Run history
st.subheader("Recent Monitor Runs")
runs = api.get_monitor_runs(limit=20)
if runs and isinstance(runs, list):
    df_data = []
    for run in runs:
        df_data.append({
            "Monitor": run.get("monitor_type", ""),
            "Brand": run.get("brand_name", ""),
            "Status": run.get("status", ""),
            "Hits": run.get("hits_found", 0),
            "Duration": f"{run.get('execution_time_seconds', 0):.1f}s",
            "Started": format_datetime(run.get("started_at", ""))[:19],
        })
    
    import pandas as pd
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No monitor runs recorded")
