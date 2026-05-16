"""Monitor status card component"""
import streamlit as st
from utils.formatters import format_relative_time


def monitor_card(monitor: dict, on_trigger=None):
    """Display a monitor status card with trigger button"""
    status_color = {
        "healthy": "#43A047",
        "degraded": "#FB8C00",
        "unhealthy": "#E53935",
    }
    
    name = monitor.get("name", monitor.get("monitor_type", "Unknown"))
    status = monitor.get("status", "unknown")
    available = monitor.get("available", False)
    success_rate = monitor.get("success_rate", 0)
    last_run = monitor.get("last_run")
    avg_time = monitor.get("avg_execution_time", 0)
    
    color = status_color.get(status, "#888")
    
    st.markdown(f"""
    <div style="background: #1a1a2e; border: 1px solid {color}44; border-radius: 10px; padding: 15px; margin: 5px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="color: {color}; font-size: 18px; font-weight: bold;">{name}</span>
                <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 10px; 
                           font-size: 12px; margin-left: 10px;">{status}</span>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 10px; color: #aaa; font-size: 13px;">
            <div>Success Rate: <span style="color: white;">{success_rate * 100:.1f}%</span></div>
            <div>Avg Time: <span style="color: white;">{avg_time:.2f}s</span></div>
            <div>Last Run: <span style="color: white;">{format_relative_time(last_run) if last_run else 'Never'}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    return st.button("Trigger", key=f"trigger_{name}", type="secondary")
