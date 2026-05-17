"""Hit detail display component"""
import streamlit as st
from utils.formatters import format_datetime


def hit_card(hit: dict, key_prefix: str = "hit"):
    """Display an expandable hit card"""
    severity_colors = {
        "CRITICAL": "#E53935",
        "HIGH": "#FB8C00", 
        "MEDIUM": "#FFB300",
        "LOW": "#43A047",
    }
    
    status_colors = {
        "pending": "#FB8C00",
        "reviewed": "#43A047",
        "false_positive": "#888",
    }
    
    hit_id = hit.get("id", "")
    brand_name = hit.get("brand_name", "Unknown")
    source = hit.get("source", "unknown")
    detected_at = hit.get("detected_at", "")
    status = hit.get("processing_status", "pending")
    content_preview = hit.get("content_preview", "")
    matched_keywords = hit.get("match_details", {}).get("matched_keywords", [])
    enrichment = hit.get("enrichment") or {}
    evaluation = enrichment.get("evaluation", {}) if enrichment else {}
    decision = enrichment.get("decision")
    severity = evaluation.get("severity")
    confidence = evaluation.get("confidence")
    
    status_color = status_colors.get(status, "#888")
    
    title_parts = [f"[{brand_name}] {source}", format_datetime(detected_at)]
    if decision:
        title_parts.append(f"LLM: {decision}")
    with st.expander(" - ".join(title_parts), expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"**Brand:** {brand_name}")
        with col2:
            st.markdown(f"**Source:** {source}")
        with col3:
            st.markdown(f"**Status:** <span style='color: {status_color}'>{status}</span>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"**LLM:** {decision or 'not processed'}")

        if enrichment:
            sev_color = severity_colors.get(severity, "#888")
            conf_text = f"{confidence:.0%}" if isinstance(confidence, (float, int)) else "N/A"
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f"**Severity:** <span style='color: {sev_color}'>{severity or 'N/A'}</span>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"**Confidence:** {conf_text}")
            with col_c:
                threat_types = evaluation.get("threat_types", [])
                st.markdown(f"**Threats:** {', '.join(threat_types) if threat_types else 'none'}")

            if evaluation.get("reasoning"):
                st.markdown("**LLM Reasoning:**")
                st.info(evaluation.get("reasoning"))
        
        if hit.get("source_url"):
            st.markdown(f"**URL:** [{hit['source_url']}]({hit['source_url']})")
        
        if matched_keywords:
            st.markdown(f"**Matched Keywords:** {', '.join(matched_keywords)}")
        
        st.markdown("**Content Preview:**")
        st.code(content_preview[:1000], language=None)
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Mark Reviewed", key=f"{key_prefix}_review_{hit_id}", type="primary"):
                return {"action": "reviewed", "hit_id": hit_id}
        with col2:
            if st.button("False Positive", key=f"{key_prefix}_fp_{hit_id}"):
                return {"action": "false_positive", "hit_id": hit_id}
    
    return None
