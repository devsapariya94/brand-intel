"""Alerts - Hit viewer with filtering"""
import streamlit as st
import pandas as pd
from api_client import BrandIntelAPI
from utils.formatters import format_datetime
from components.hit_viewer import hit_card

st.set_page_config(page_title="Alerts", page_icon=":rotating_light:", layout="wide")

@st.cache_resource
def get_api():
    return BrandIntelAPI()

api = get_api()

st.title(":rotating_light: Alerts & Hits")

# Fetch brands for filter
brands = api.list_brands()
brand_options = {"All Brands": None}
if brands and isinstance(brands, list):
    for b in brands:
        brand_options[b["name"]] = b["id"]

# Filter bar
with st.container(border=True):
    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 1, 1, 1, 1])
    
    with col1:
        brand_filter = st.selectbox("Brand", list(brand_options.keys()))
    
    with col2:
        status_filter = st.selectbox("Status", ["All", "pending", "reviewed", "false_positive"])
    
    with col3:
        source_filter = st.selectbox("Source", ["All", "github", "hackernews", "ransomware", "xposedornot", "intelx"])
    
    with col4:
        decision_filter = st.selectbox("LLM", ["All", "ALERT", "ESCALATE", "SUPPRESS", "Not processed"])

    with col5:
        severity_filter = st.selectbox("Severity", ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"])

    with col6:
        limit = st.selectbox("Limit", [10, 25, 50, 100], index=2)
    
    with col7:
        if st.button("Apply Filters", type="primary", use_container_width=True):
            st.session_state.apply_filters = True

# Fetch hits stats
hits_stats = api.get_hits_stats()

# Stats summary
if hits_stats and not isinstance(hits_stats, dict) or (hits_stats and "error" not in hits_stats):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Hits", hits_stats.get("total_hits", 0) if hits_stats else 0)
    with col2:
        by_status = hits_stats.get("by_status", {}) if hits_stats else {}
        st.metric("Pending", by_status.get("pending", 0))
    with col3:
        st.metric("Reviewed", by_status.get("reviewed", 0))
    with col4:
        st.metric("False Positive", by_status.get("false_positive", 0))

st.divider()

# Fetch hits
brand_id = brand_options.get(brand_filter)
status = None if status_filter == "All" else status_filter
source = None if source_filter == "All" else source_filter

hits_data = api.list_hits(brand_id=brand_id, status=status, source=source, limit=limit)

if hits_data and "hits" in hits_data:
    hits = hits_data["hits"]
    if decision_filter != "All":
        if decision_filter == "Not processed":
            hits = [h for h in hits if not h.get("enrichment")]
        else:
            hits = [h for h in hits if (h.get("enrichment") or {}).get("decision") == decision_filter]
    if severity_filter != "All":
        hits = [
            h for h in hits
            if ((h.get("enrichment") or {}).get("evaluation") or {}).get("severity") == severity_filter
        ]
    total = hits_data.get("total", 0)
    page = hits_data.get("page", 1)
    
    st.caption(f"Showing {len(hits)} of {total} hits")
    
    # Display hits
    for hit in hits:
        result = hit_card(hit, key_prefix="alerts")
        
        if result:
            action = result["action"]
            hit_id = result["hit_id"]
            
            with st.spinner("Updating..."):
                update_result = api.update_hit_status(hit_id, action)
            
            if update_result and "error" not in update_result:
                st.success(f"Marked as {action}")
                st.rerun()
            else:
                st.error("Failed to update status")
    
    # Pagination
    if hits_data.get("has_next") or hits_data.get("has_prev"):
        st.divider()
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if hits_data.get("has_prev"):
                if st.button("Previous Page"):
                    st.session_state.page = max(1, page - 1)
        with col2:
            st.markdown(f"<div style='text-align: center; padding: 10px;'>Page {page}</div>", unsafe_allow_html=True)
        with col3:
            if hits_data.get("has_next"):
                if st.button("Next Page"):
                    st.session_state.page = page + 1
    
    # Export
    st.divider()
    if st.button("Export to CSV"):
        df_data = []
        for hit in hits:
            df_data.append({
                "Brand": hit.get("brand_name", ""),
                "Source": hit.get("source", ""),
                "Status": hit.get("processing_status", ""),
                "Detected At": hit.get("detected_at", ""),
                "URL": hit.get("source_url", ""),
                "Keywords": ", ".join(hit.get("match_details", {}).get("matched_keywords", [])),
                "Preview": hit.get("content_preview", "")[:200],
            })
        
        df = pd.DataFrame(df_data)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "hits_export.csv", "text/csv")

else:
    st.info("No hits found matching filters")
