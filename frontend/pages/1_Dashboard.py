"""Dashboard - System overview and metrics"""
import streamlit as st
import pandas as pd
from api_client import BrandIntelAPI
from config import REFRESH_INTERVAL
from components.metric_cards import display_metrics
from components.stats_charts import hits_timeline, source_bar_chart

st.set_page_config(page_title="Dashboard", page_icon=":chart_with_upwards_trend:", layout="wide")

# Initialize API
@st.cache_resource
def get_api():
    return BrandIntelAPI()

api = get_api()

st.title(":chart_with_upwards_trend: Dashboard")

# Fetch data
metrics = api.get_metrics()
hits_stats = api.get_hits_stats(days=7)
monitor_status = api.get_monitor_status()

if not metrics or "error" in metrics:
    st.error("Failed to fetch metrics. Ensure backend is running.")
    st.stop()

# Key metrics
display_metrics([
    {"label": "Total Brands", "value": metrics.get("total_brands", 0), "icon": ":building:", "color": "blue"},
    {"label": "Total Alerts", "value": metrics.get("total_hits", 0), "icon": ":warning:", "color": "orange"},
    {"label": "Success Rate", "value": f"{metrics.get('success_rate', 0) * 100:.1f}%", "icon": ":white_check_mark:", "color": "green"},
    {"label": "DLQ Pending", "value": metrics.get("dlq_pending", 0), "icon": ":inbox:", "color": "red" if metrics.get("dlq_pending", 0) > 0 else "green"},
])

st.divider()

# Monitor status and timeline
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Monitor Status")
    if monitor_status and "monitors" in monitor_status:
        for monitor in monitor_status["monitors"]:
            status = monitor.get("status", "unknown")
            status_color = {"healthy": ":green_circle:", "degraded": ":orange_circle:", "unhealthy": ":red_circle:"}.get(status, ":gray_circle:")
            
            with st.container(border=True):
                col_a, col_b, col_c = st.columns([2, 1, 1])
                with col_a:
                    st.markdown(f"{status_color} **{monitor.get('name', 'Unknown')}**")
                with col_b:
                    st.metric("Success", f"{monitor.get('success_rate', 0) * 100:.0f}%")
                with col_c:
                    st.metric("Avg Time", f"{monitor.get('avg_execution_time', 0):.1f}s")
    else:
        st.info("No monitors configured")

with col2:
    st.subheader("7-Day Hit Trend")
    if hits_stats and hits_stats.get("timeline"):
        hits_timeline(hits_stats["timeline"])
    else:
        st.info("No hit data yet. Run monitors to see trends.")

st.divider()

# Source breakdown and recent hits
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Hits by Source")
    if hits_stats and hits_stats.get("by_source"):
        source_bar_chart(hits_stats["by_source"])
    else:
        st.info("No source data available")

with col2:
    st.subheader("Top Keywords")
    if hits_stats and hits_stats.get("top_keywords"):
        df = pd.DataFrame(hits_stats["top_keywords"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No keyword data available")

st.divider()

# Recent hits
st.subheader("Recent Hits")
recent_hits = api.list_hits(limit=5)
if recent_hits and "hits" in recent_hits:
    for hit in recent_hits["hits"]:
        status_colors = {"pending": "orange", "reviewed": "green", "false_positive": "gray"}
        color = status_colors.get(hit.get("processing_status", "pending"), "gray")
        
        cols = st.columns([2, 1, 1, 1])
        with cols[0]:
            st.markdown(f"**{hit.get('brand_name', 'Unknown')}** - {hit.get('source', 'unknown')}")
        with cols[1]:
            st.markdown(f":{color}[{hit.get('processing_status', 'pending')}]")
        with cols[2]:
            st.caption(hit.get("detected_at", "")[:19])
        with cols[3]:
            keywords = hit.get("match_details", {}).get("matched_keywords", [])
            st.caption(", ".join(keywords[:3]) if keywords else "-")
else:
    st.info("No hits recorded yet")
