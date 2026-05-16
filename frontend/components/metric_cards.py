"""Dashboard metric cards component"""
import streamlit as st


def metric_card(label: str, value: str, icon: str = "", delta: str = None, color: str = "blue"):
    """Display a metric card"""
    color_map = {
        "blue": "#1E88E5",
        "green": "#43A047",
        "red": "#E53935",
        "orange": "#FB8C00",
        "purple": "#8E24AA",
    }
    bg_color = color_map.get(color, "#1E88E5")
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {bg_color}22, {bg_color}11); 
                border: 1px solid {bg_color}44; border-radius: 10px; padding: 20px; margin: 5px 0;">
        <div style="color: #888; font-size: 14px; margin-bottom: 8px;">{icon} {label}</div>
        <div style="color: white; font-size: 32px; font-weight: bold;">{value}</div>
        {f'<div style="color: {"#43A047" if delta and not delta.startswith("-") else "#E53935"}; font-size: 14px; margin-top: 5px;">{delta}</div>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)


def display_metrics(metrics: list):
    """Display a row of metric cards
    
    Args:
        metrics: List of dicts with keys: label, value, icon, delta (optional), color (optional)
    """
    cols = st.columns(len(metrics))
    for i, col in enumerate(cols):
        if i < len(metrics):
            m = metrics[i]
            with col:
                metric_card(
                    label=m.get("label", ""),
                    value=str(m.get("value", "0")),
                    icon=m.get("icon", ""),
                    delta=m.get("delta"),
                    color=m.get("color", "blue")
                )
