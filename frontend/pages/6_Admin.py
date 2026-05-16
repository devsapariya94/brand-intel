"""Admin - System administration"""
import streamlit as st
from api_client import BrandIntelAPI
from utils.formatters import format_datetime, format_relative_time

st.set_page_config(page_title="Admin", page_icon=":gear:", layout="wide")

@st.cache_resource
def get_api():
    return BrandIntelAPI()

api = get_api()

st.title(":gear: Administration")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Health", "Dead Letter Queue", "Circuit Breaker", "Maintenance"])

with tab1:
    st.subheader("System Health")
    
    health = api.get_detailed_health()
    
    if health and "error" not in health:
        # Overall status
        status = health.get("status", "unknown")
        status_color = {"healthy": "green", "degraded": "orange", "unhealthy": "red"}.get(status, "gray")
        st.markdown(f"### :{status_color}[{status.upper()}]")
        
        # Database health
        db = health.get("database", {})
        st.markdown(f"**Database:** :{db.get('status', 'unknown')}[ {db.get('status', 'unknown').upper()}]")
        
        # Monitor health
        st.markdown("**Monitors:**")
        monitors = health.get("monitors", {})
        for name, mhealth in monitors.items():
            color = mhealth.get("status", "unknown")
            st.markdown(f"  - {name}: :{color}[{color.upper()}]")
        
        # DLQ health
        dlq = health.get("dlq", {})
        st.markdown(f"**DLQ:** {dlq.get('pending', 0)} pending, {dlq.get('failed', 0)} failed")
        
        # Uptime
        uptime = health.get("uptime_seconds", 0)
        if uptime > 0:
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            st.markdown(f"**Uptime:** {hours}h {minutes}m")
        
        # Last scan
        last_scan = health.get("last_scan")
        if last_scan:
            st.markdown(f"**Last Scan:** {format_datetime(last_scan)}")
    else:
        st.error("Failed to fetch health data")

with tab2:
    st.subheader("Dead Letter Queue")
    
    dlq_items = api.get_dlq_items()
    
    if dlq_items and isinstance(dlq_items, list) and len(dlq_items) > 0:
        st.caption(f"{len(dlq_items)} items in DLQ")
        
        for item in dlq_items:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
                
                with col1:
                    st.markdown(f"**{item.get('brand_name', 'Unknown')}**")
                    st.caption(f"Source: {item.get('source', 'unknown')}")
                
                with col2:
                    st.caption(f"Retries: {item.get('retry_count', 0)}/{item.get('max_retries', 3)}")
                
                with col3:
                    st.caption(f"Status: {item.get('status', 'pending')}")
                
                with col4:
                    st.caption(f"Created: {format_datetime(item.get('created_at', ''))[:19]}")
                
                with col5:
                    if st.button("Retry", key=f"dlq_retry_{item['id']}", type="primary"):
                        result = api.retry_dlq_item(item["id"])
                        if result and "error" not in result:
                            st.success("Retry queued")
                        else:
                            st.error("Retry failed")
                    
                    if st.button("Delete", key=f"dlq_del_{item['id']}"):
                        result = api.delete_dlq_item(item["id"])
                        if result and "error" not in result:
                            st.success("Item deleted")
                            st.rerun()
                        else:
                            st.error("Delete failed")
                
                # Error message
                if item.get("error"):
                    st.error(item["error"])
    else:
        st.success("DLQ is empty")

with tab3:
    st.subheader("Circuit Breaker Management")
    
    monitor_status = api.get_monitor_status()
    cb_states = monitor_status.get("circuit_breaker", {}) if monitor_status else {}
    
    if cb_states:
        for monitor_type, state in cb_states.items():
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
                
                state_val = state.get("state", "closed")
                state_color = {"closed": "green", "open": "red", "half_open": "orange"}.get(state_val, "gray")
                
                with col1:
                    st.markdown(f"**{monitor_type}**")
                
                with col2:
                    st.markdown(f":{state_color}[{state_val.upper()}]")
                
                with col3:
                    st.caption(f"Failures: {state.get('failure_count', 0)}")
                    if state.get("last_failure"):
                        st.caption(f"Last failure: {format_datetime(state['last_failure'])[:19]}")
                
                with col4:
                    if state_val == "open":
                        if st.button("Reset", key=f"admin_cb_reset_{monitor_type}"):
                            result = api.reset_circuit_breaker(monitor_type)
                            if result and "error" not in result:
                                st.success(f"Reset {monitor_type}")
                            else:
                                st.error("Reset failed")
    else:
        st.info("No circuit breaker data available")

with tab4:
    st.subheader("Maintenance Tasks")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Cleanup Old Data**")
        st.caption("Remove monitor runs older than 30 days")
        if st.button("Run Cleanup", type="primary"):
            with st.spinner("Running cleanup..."):
                result = api.trigger_cleanup()
            if result and "error" not in result:
                st.success(f"Cleanup complete. Deleted {result.get('monitor_runs_deleted', 0)} old runs.")
            else:
                st.error("Cleanup failed")
    
    with col2:
        st.markdown("**System Information**")
        st.caption("API and system details")
        
        root = api._get("/")
        if root and "error" not in root:
            st.json({
                "API Name": root.get("name", ""),
                "Version": root.get("version", ""),
                "Status": root.get("status", ""),
            })
