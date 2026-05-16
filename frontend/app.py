"""Brand Intel Monitor - Main Streamlit App"""
import streamlit as st
from api_client import BrandIntelAPI
from config import APP_TITLE, REFRESH_INTERVAL

# Page config
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=":shield:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {padding-top: 2rem;}
    [data-testid="stSidebar"] {background-color: #0d1117;}
    .stExpander {border: 1px solid #30363d;}
    div[data-testid="stMetricValue"] {font-size: 2rem !important;}
    .css-1aumxhk {background-color: #0d1117;}
    .stButton > button {border-radius: 8px;}
    .success-box {padding: 1rem; border-radius: 8px; background: #1B4332; border: 1px solid #43A047;}
    .error-box {padding: 1rem; border-radius: 8px; background: #4A1C1C; border: 1px solid #E53935;}
    .warning-box {padding: 1rem; border-radius: 8px; background: #4A3C1C; border: 1px solid #FB8C00;}
</style>
""", unsafe_allow_html=True)

# Initialize API client
@st.cache_resource
def get_api_client():
    return BrandIntelAPI()

api = get_api_client()

# Sidebar
with st.sidebar:
    st.title(":shield: Brand Intel")
    st.caption("Threat Monitoring Dashboard")
    
    st.divider()
    
    # Connection status
    health = api.get_health()
    if health and "error" not in health:
        st.success("API Connected")
    else:
        st.error("API Disconnected")
        st.caption("Ensure backend is running on http://localhost:8000")
    
    st.divider()
    
    st.caption(f"Auto-refresh: {REFRESH_INTERVAL}s")
    
    if st.button("Refresh Now", use_container_width=True):
        st.rerun()

# Title
st.title(":shield: Brand Intel Monitor")
