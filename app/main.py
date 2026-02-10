"""
SARAL-TN Streamlit App
Fixed version - buttons outside forms
"""

import streamlit as st
import uuid
from datetime import datetime

# Page config
st.set_page_config(
    page_title="SARAL-TN | AI Traffic Enforcement",
    page_icon="🚦",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .violation-card {
        background-color: #ffebee;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f44336;
        margin: 0.5rem 0;
    }
    .success-card {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False
if 'challan_generated' not in st.session_state:
    st.session_state.challan_generated = False

# Header
st.markdown('<p class="main-header">🚦 SARAL-TN</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Simple, Accessible, Responsive, AI-Led Traffic Enforcement</p>',
    unsafe_allow_html=True
)

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Violations Detected", "12,450+")
with col2:
    st.metric("Revenue Generated", "₹1.2 Cr")
with col3:
    st.metric("Active Reporters", "3,200+")
with col4:
    st.metric("Detection Accuracy", "97.9%")

st.divider()

# Main tabs
tab1, tab2, tab3 = st.tabs(["🚨 Report Violation", "📈 Dashboard", "🏆 Leaderboard"])

with tab1:
    st.header("📹 Report Traffic Violation")
    
    # Form for inputs only
    with st.form("violation_report"):
        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input("Mobile Number", placeholder="9876543210")
        with col2:
            location = st.text_input("Location", placeholder="T. Nagar, Chennai")
        
        uploaded_file = st.file_uploader(
            "Upload Violation Video",
            type=['mp4', 'mov', 'avi'],
            help="Max 50MB. Show clear view of violation and license plate."
        )
        
        gps_consent = st.checkbox("I confirm this video was recorded at the violation location", value=True)
        
        # Submit button INSIDE form (this is OK)
        submitted = st.form_submit_button("🚀 Process Violation", use_container_width=True)
    
    # Processing happens AFTER form, OUTSIDE form
    if submitted:
        if not phone or len(phone) != 10:
            st.error("Please enter valid 10-digit mobile number")
        elif not uploaded_file:
            st.error("Please upload a video")
        else:
            # Simulate processing
            with st.spinner("🔍 AI Processing... (~45 seconds)"):
                import time
                time.sleep(2)  # Simulate AI processing
                
                # Store in session state
                st.session_state.processing_done = True
                st.session_state.phone = phone
                st.session_state.location = location
                st.success("✅ Violation Detected!")
    
    # Show results OUTSIDE form (buttons can be here)
    if st.session_state.processing_done:
        st.markdown('<div class="violation-card">', unsafe_allow_html=True)
        st.subheader("🎯 Detection Results")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("**Violation Type:** Red Light Jump")
            st.write("**AI Confidence:** 94.5%")
            st.write("**License Plate:** TN-09-BZ-1234")
            st.write("**Plate Confidence:** 89.2%")
        
        with col2:
            st.metric("Fine Amount", "₹1,000")
            st.metric("Your Reward", "₹100", delta="10%")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Generate challan button OUTSIDE form (this is OK)
        if st.button("📄 Generate E-Challan", type="primary"):
            st.session_state.challan_generated = True
    
    # Show challan OUTSIDE form
    if st.session_state.challan_generated:
        st.balloons()
        st.markdown('<div class="success-card">', unsafe_allow_html=True)
        st.success("E-Challan Generated!")
        st.write(f"**Challan ID:** TN{datetime.now().strftime('%Y%m%d')}1234")
        st.write("SMS sent to vehicle owner")
        st.info("🎉 ₹100 reward will be credited to your FASTag in 24 hours!")
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.header("📊 Enforcement Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Violations by Type")
        chart_data = {
            "No Helmet": 45,
            "Red Light": 30,
            "Wrong Side": 15,
            "Others": 10
        }
        st.bar_chart(chart_data)
    
    with col2:
        st.subheader("Daily Reports")
        st.line_chart([12, 15, 18, 22, 25, 30, 35])

with tab3:
    st.header("🏆 Top Road Guardians")
    
    leaderboard = [
        {"rank": 1, "name": "Ramesh K.", "reports": 45, "reward": "₹4,500"},
        {"rank": 2, "name": "Priya M.", "reports": 38, "reward": "₹3,800"},
        {"rank": 3, "name": "Kumar S.", "reports": 32, "reward": "₹3,200"},
    ]
    
    for entry in leaderboard:
        cols = st.columns([1, 3, 2, 2])
        cols[0].write(f"#{entry['rank']}")
        cols[1].write(entry['name'])
        cols[2].write(f"{entry['reports']} reports")
        cols[3].write(entry['reward'])

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/TamilNadu_Logo.svg/1200px-TamilNadu_Logo.svg.png", width=100)
    st.title("SARAL-TN")
    st.caption("Government of Tamil Nadu")
    
    st.divider()
    
    st.header("📊 Your Stats")
    st.write(f"**Reporter ID:** `{st.session_state.user_id}`")
    st.write("**Reports Submitted:** 0")
    st.write("**Rewards Earned:** ₹0")
    st.write("**Leaderboard Rank:** #--")
    
    st.divider()
    
    st.header("ℹ️ How It Works")
    st.markdown("""
    1. 📹 Record traffic violation
    2. 📤 Upload video with GPS
    3. 🤖 AI detects & reads plate
    4. 📄 E-challan auto-generated
    5. 💰 Earn 10% as reward!
    """)
    
    st.divider()
    
    st.header("📞 Support")
    st.write("Greater Chennai Traffic Police")
    st.write("📱 044-2345xxxx")
    st.write("📧 saral-tn@gov.in")
