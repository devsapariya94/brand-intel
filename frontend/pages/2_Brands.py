"""Brands - Brand management"""
import streamlit as st
from api_client import BrandIntelAPI
from components.brand_form import brand_form

st.set_page_config(page_title="Brands", page_icon=":building:", layout="wide")

@st.cache_resource
def get_api():
    return BrandIntelAPI()

api = get_api()

st.title(":building: Brand Management")

# Tabs
tab1, tab2 = st.tabs(["All Brands", "Add New Brand"])

with tab1:
    # Search and filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search brands", placeholder="Search by name or domain...")
    with col2:
        active_only = st.checkbox("Active only", value=True)
    
    # Fetch brands
    brands = api.list_brands(active_only=active_only)
    
    if not brands or "error" in brands:
        st.warning("No brands found" if brands else "Failed to fetch brands")
    else:
        # Filter by search
        if search:
            brands = [b for b in brands if search.lower() in b.get("name", "").lower() 
                     or search.lower() in b.get("domain", "").lower()]
        
        # Display brands
        for brand in brands:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{brand['name']}**")
                    st.caption(brand.get("domain", ""))
                
                with col2:
                    status = ":green_circle: Active" if brand.get("active") else ":red_circle: Inactive"
                    st.markdown(status)
                
                with col3:
                    stats = brand.get("stats", {})
                    st.metric("Hits", stats.get("total_hits", 0))
                
                with col4:
                    st.metric("24h", stats.get("hits_last_24h", 0))
                
                with col5:
                    if st.button("Edit", key=f"edit_{brand['id']}"):
                        st.session_state[f"editing_{brand['id']}"] = True
                    if st.button("Delete", key=f"del_{brand['id']}", type="secondary"):
                        st.session_state[f"deleting_{brand['id']}"] = True
                
                # Expanded details
                with st.expander("Details"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Keywords:**")
                        st.write(", ".join(brand.get("keywords", [])) or "None")
                        st.markdown("**Email Patterns:**")
                        st.write(", ".join(brand.get("email_patterns", [])) or "None")
                    with col_b:
                        st.markdown("**Regex Patterns:**")
                        st.write(", ".join(brand.get("regex_patterns", [])) or "None")
                        st.markdown("**Typosquat Variants:**")
                        st.write(", ".join(brand.get("typosquat_variants", [])) or "None")
                    
                    if brand.get("slack_webhook"):
                        st.markdown(f"**Slack Webhook:** Configured")
                    if brand.get("alert_email"):
                        st.markdown(f"**Alert Email:** {brand['alert_email']}")
                
                # Handle delete confirmation
                if st.session_state.get(f"deleting_{brand['id']}"):
                    st.warning(f"Are you sure you want to delete **{brand['name']}**?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Confirm Delete", type="primary", key=f"confirm_del_{brand['id']}"):
                            result = api.delete_brand(brand["id"])
                            if result and "error" not in result:
                                st.success("Brand deleted")
                                st.session_state[f"deleting_{brand['id']}"] = False
                                st.rerun()
                            else:
                                st.error("Failed to delete brand")
                    with col_no:
                        if st.button("Cancel", key=f"cancel_del_{brand['id']}"):
                            st.session_state[f"deleting_{brand['id']}"] = False
                            st.rerun()
                
                # Handle edit
                if st.session_state.get(f"editing_{brand['id']}"):
                    st.subheader(f"Edit: {brand['name']}")
                    edit_data = brand_form(brand=brand, submit_label="Update Brand")
                    if edit_data:
                        result = api.update_brand(brand["id"], edit_data)
                        if result and "error" not in result:
                            st.success("Brand updated")
                            st.session_state[f"editing_{brand['id']}"] = False
                            st.rerun()
                        else:
                            st.error("Failed to update brand")
                    if st.button("Cancel Edit", key=f"cancel_edit_{brand['id']}"):
                        st.session_state[f"editing_{brand['id']}"] = False
                        st.rerun()

with tab2:
    st.subheader("Add New Brand")
    new_brand = brand_form(submit_label="Create Brand")
    if new_brand:
        result = api.create_brand(new_brand)
        if result and "error" not in result:
            st.success(f"Brand '{new_brand['name']}' created successfully!")
            st.rerun()
        else:
            st.error(f"Failed to create brand: {result.get('error', result.get('detail', 'Unknown error'))")
