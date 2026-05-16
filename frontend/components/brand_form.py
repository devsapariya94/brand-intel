"""Brand create/edit form component"""
import streamlit as st
from utils.validators import validate_domain, validate_email, validate_keywords


def brand_form(brand: dict = None, submit_label: str = "Create Brand"):
    """Display a brand form for create or edit
    
    Returns:
        dict with brand data if submitted, None otherwise
    """
    with st.form("brand_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Brand Name *", value=brand.get("name", "") if brand else "", 
                                help="Display name for the brand")
            domain = st.text_input("Domain *", value=brand.get("domain", "") if brand else "",
                                  help="Primary domain (e.g., example.com)")
            alert_email = st.text_input("Alert Email", value=brand.get("alert_email", "") if brand else "",
                                       help="Email for critical alerts")
        
        with col2:
            slack_webhook = st.text_input("Slack Webhook URL", 
                                         value=brand.get("slack_webhook", "") if brand else "",
                                         help="Slack webhook for notifications")
            keywords_str = st.text_area("Keywords (comma-separated)", 
                                       value=", ".join(brand.get("keywords", [])) if brand else "",
                                       help="Keywords to monitor for")
        
        # Advanced options
        with st.expander("Advanced Options"):
            email_patterns_str = st.text_area("Email Patterns (comma-separated)",
                                             value=", ".join(brand.get("email_patterns", [])) if brand else "",
                                             help="Email patterns to detect")
            regex_patterns_str = st.text_area("Regex Patterns (one per line)",
                                             value="\n".join(brand.get("regex_patterns", [])) if brand else "",
                                             help="Custom regex patterns")
            typosquat_str = st.text_area("Typosquat Variants (comma-separated)",
                                        value=", ".join(brand.get("typosquat_variants", [])) if brand else "",
                                        help="Common typosquat domains")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                monitor_pastebin = st.checkbox("Pastebin Monitor", 
                                              value=brand.get("monitor_config", {}).get("pastebin", True) if brand else True)
            with col2:
                monitor_github = st.checkbox("GitHub Monitor",
                                            value=brand.get("monitor_config", {}).get("github", True) if brand else True)
            with col3:
                monitor_reddit = st.checkbox("Reddit Monitor",
                                            value=brand.get("monitor_config", {}).get("reddit", True) if brand else True)
        
        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)
        
        if submitted:
            if not name or not domain:
                st.error("Brand Name and Domain are required")
                return None
            
            if not validate_domain(domain):
                st.error("Invalid domain format")
                return None
            
            if alert_email and not validate_email(alert_email):
                st.error("Invalid email format")
                return None
            
            keywords = validate_keywords(keywords_str) if keywords_str else []
            email_patterns = validate_keywords(email_patterns_str) if email_patterns_str else []
            regex_patterns = [r.strip() for r in regex_patterns_str.split("\n") if r.strip()] if regex_patterns_str else []
            typosquat_variants = validate_keywords(typosquat_str) if typosquat_str else []
            
            return {
                "name": name,
                "domain": domain,
                "keywords": keywords,
                "email_patterns": email_patterns,
                "regex_patterns": regex_patterns,
                "typosquat_variants": typosquat_variants,
                "slack_webhook": slack_webhook if slack_webhook else None,
                "alert_email": alert_email if alert_email else None,
                "monitor_config": {
                    "pastebin": monitor_pastebin,
                    "github": monitor_github,
                    "reddit": monitor_reddit,
                    "hibp": True
                }
            }
    
    return None
