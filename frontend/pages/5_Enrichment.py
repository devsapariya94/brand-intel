"""Enrichment - AI enrichment configuration"""
import streamlit as st
from api_client import BrandIntelAPI
from components.stats_charts import severity_pie_chart

st.set_page_config(page_title="Enrichment", page_icon=":brain:", layout="wide")

@st.cache_resource
def get_api():
    return BrandIntelAPI()

api = get_api()

st.title(":brain: AI Enrichment")

# Fetch config and stats
config = api.get_enrichment_config()
stats = api.get_enrichment_stats()

if not config or "error" in config:
    st.warning("Could not fetch enrichment configuration")

# Configuration
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Configuration")
    
    if config and "error" not in config:
        with st.container(border=True):
            st.markdown(f"**Provider:** {'Anthropic' if config.get('use_anthropic') else 'OpenAI-compatible'}")
            st.markdown(f"**Model:** {config.get('llm_model', 'N/A')}")
            st.markdown(f"**Temperature:** {config.get('llm_temperature', 0.3)}")
            
            st.divider()
            
            st.markdown("**Thresholds:**")
            st.progress(config.get("alert_threshold", 0.85), text=f"Alert: {config.get('alert_threshold', 0.85):.2f}")
            st.progress(config.get("suppress_threshold", 0.85), text=f"Suppress: {config.get('suppress_threshold', 0.85):.2f}")
            st.progress(config.get("escalate_threshold", 0.60), text=f"Escalate: {config.get('escalate_threshold', 0.60):.2f}")
    
    st.divider()
    
    # Update config form
    with st.expander("Update Configuration"):
        with st.form("enrichment_config_form"):
            llm_model = st.text_input("LLM Model", value=config.get("llm_model", "gpt-4o") if config else "gpt-4o")
            temperature = st.slider("Temperature", 0.0, 2.0, config.get("llm_temperature", 0.3) if config else 0.3, 0.1)
            
            st.markdown("**Decision Thresholds:**")
            alert_threshold = st.slider("Alert Threshold", 0.0, 1.0, config.get("alert_threshold", 0.85) if config else 0.85, 0.05)
            suppress_threshold = st.slider("Suppress Threshold", 0.0, 1.0, config.get("suppress_threshold", 0.85) if config else 0.85, 0.05)
            escalate_threshold = st.slider("Escalate Threshold", 0.0, 1.0, config.get("escalate_threshold", 0.60) if config else 0.60, 0.05)
            
            if st.form_submit_button("Update Config", type="primary"):
                update_data = {
                    "llm_model": llm_model,
                    "llm_temperature": temperature,
                    "alert_threshold": alert_threshold,
                    "suppress_threshold": suppress_threshold,
                    "escalate_threshold": escalate_threshold,
                }
                result = api.update_enrichment_config(update_data)
                if result and "error" not in result:
                    st.success("Configuration updated")
                else:
                    st.error("Failed to update configuration")

with col2:
    st.subheader("Statistics")
    
    if stats and "error" not in stats:
        # Stats cards
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Total Processed", stats.get("total_processed", 0))
        with col_b:
            st.metric("Avg Processing Time", f"{stats.get('avg_processing_time', 0):.2f}s")
        with col_c:
            st.metric("Est. Cost", f"${stats.get('estimated_cost', 0):.4f}")
        
        st.divider()
        
        # Pie chart
        severity_pie_chart(stats)
    else:
        st.info("No enrichment statistics available")

st.divider()

# Manual processing
st.subheader("Manual Processing")
st.caption("Process a specific hit through the enrichment pipeline")

col1, col2 = st.columns([2, 1])
with col1:
    hit_id = st.text_input("Hit ID", placeholder="Enter hit ID to process")
with col2:
    if st.button("Process Hit", type="primary", use_container_width=True):
        if hit_id:
            with st.spinner("Processing..."):
                result = api.process_hit(hit_id)
            if result and "error" not in result:
                st.success(f"Decision: {result.get('decision', 'N/A')}")
                st.info(f"Reasoning: {result.get('reasoning', 'N/A')}")
            else:
                st.error(f"Processing failed: {result}")
        else:
            st.warning("Please enter a hit ID")
