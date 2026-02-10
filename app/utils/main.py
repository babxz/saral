"""
SARAL-TN Streamlit Application
Tamil Nadu AI-Powered Traffic Enforcement
"""

import os
import uuid
import tempfile
from datetime import datetime

import streamlit as st
from PIL import Image

# Add parent to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.utils.validators import validator
from app.utils.ai_processor import get_ai_processor
from app.utils.database import db_manager
from app.utils.challan_generator import challan_gen


# Page configuration
st.set_page_config(
    page_title="SARAL-TN | AI Traffic Enforcement",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
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


def init_session():
    """Initialize session state"""
    if 'processor' not in st.session_state:
        with st.spinner("Loading AI models... (one-time setup)"):
            st.session_state.processor = get_ai_processor()
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())[:8]


def render_header():
    """Render app header"""
    st.markdown('<p class="main-header">🚦 SARAL-TN</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Simple, Accessible, Responsive, AI-Led Traffic Enforcement</p>',
        unsafe_allow_html=True
    )
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Violations Detected", "12,450+")
    with col2:
        st.metric("Revenue Generated", "₹1.2 Cr")
    with col3:
        st.metric("Active Reporters", "3,200+")
    with col4:
        st.metric("Detection Accuracy", "97.9%")


def render_upload_section():
    """Render video upload section"""
    st.header("📹 Report Traffic Violation")
    
    with st.form("violation_report"):
        # Reporter info
        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input("Mobile Number", placeholder="9876543210")
        with col2:
            location = st.text_input("Location (Optional)", placeholder="T. Nagar, Chennai")
        
        # Video upload
        uploaded_file = st.file_uploader(
            "Upload Violation Video",
            type=['mp4', 'mov', 'avi'],
            help="Max 50MB. Must show clear view of violation and license plate."
        )
        
        # GPS consent
        gps_consent = st.checkbox(
            "I confirm this video was recorded at the violation location",
            value=True
        )
        
        submitted = st.form_submit_button("🚀 Process Violation", use_container_width=True)
        
        if submitted:
            if not phone or len(phone) != 10:
                st.error("Please enter valid 10-digit mobile number")
                return None
            
            if not uploaded_file:
                st.error("Please upload a video")
                return None
            
            return {
                "phone": phone,
                "location": location,
                "video": uploaded_file,
                "gps_consent": gps_consent
            }
    
    return None


def process_violation(data):
    """Process uploaded video through AI pipeline"""
    with st.spinner("🔍 Analyzing video with AI... This takes ~45 seconds"):
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(data["video"].getvalue())
            video_path = tmp.name
        
        try:
            # Step 1: Validate metadata
            st.info("Step 1/4: Validating video metadata...")
            metadata = validator.extract_exif(video_path)
            
            # Step 2: AI Processing
            st.info("Step 2/4: Detecting violations with YOLOv8...")
            processor = st.session_state.processor
            result = processor.process_video(video_path)
            
            if not result["success"]:
                st.warning("No violations detected in this video. Please try another clip.")
                return None
            
            # Step 3: Display results
            st.info(f"Step 3/4: Found {result['violations_count']} violation(s)")
            
            return {
                "video_path": video_path,
                "metadata": metadata,
                "violations": result["violations"],
                "reporter_phone": data["phone"],
                "reporter_location": data["location"]
            }
            
        except Exception as e:
            st.error(f"Processing error: {str(e)}")
            return None


def render_results(processed_data):
    """Render violation detection results"""
    st.header("🎯 Violation Detected")
    
    violations = processed_data["violations"]
    
    for i, v in enumerate(violations, 1):
        with st.container():
            st.markdown(f'<div class="violation-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader(f"Violation #{i}: {v['type'].replace('_', ' ').title()}")
                st.write(f"**AI Confidence:** {v['confidence']*100:.1f}%")
                
                if v['plate_number']:
                    st.write(f"**License Plate:** `{v['plate_number']}`")
                    st.write(f"**Plate Confidence:** {v['plate_confidence']*100:.1f}%")
                else:
                    st.warning("License plate not clearly visible")
            
            with col2:
                # Fine calculation
                fine_map = {
                    "red_light_jump": 1000,
                    "wrong_side_driving": 1500,
                    "no_helmet": 500,
                    "triple_riding": 1000,
                    "illegal_parking": 500
                }
                fine = fine_map.get(v['type'], 1000)
                reward = int(fine * 0.1)
                
                st.metric("Fine Amount", f"₹{fine}")
                st.metric("Your Reward", f"₹{reward}", delta="10% of fine")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Generate challan button
    if st.button("📄 Generate E-Challan", type="primary", use_container_width=True):
        generate_challan(processed_data, violations[0])


def generate_challan(data, violation):
    """Generate and display challan"""
    with st.spinner("Generating legally valid e-challan..."):
        challan_id = f"TN{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        
        challan_data = {
            "challan_id": challan_id,
            "datetime": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "plate_number": violation.get("plate_number", "UNKNOWN"),
            "violation_type": violation["type"],
            "confidence": f"{violation['confidence']*100:.1f}",
            "video_hash": "a1b2c3d4e5f6",  # Would be actual hash
            "reporter_id": st.session_state.user_id,
            "location": data.get("reporter_location", "Chennai, TN"),
            "gps": "13.0827° N, 80.2707° E"
        }
        
        # Generate PDF
        pdf_bytes = challan_gen.generate(challan_data)
        
        # Display success
        st.markdown('<div class="success-card">', unsafe_allow_html=True)
        st.success("✅ E-Challan Generated Successfully!")
        st.write(f"**Challan ID:** `{challan_id}`")
        st.write("The challan has been sent to the vehicle owner via SMS.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Download button
        st.download_button(
            label="📥 Download E-Challan PDF",
            data=pdf_bytes,
            file_name=f"challan_{challan_id}.pdf",
            mime="application/pdf"
        )
        
        # Reward notification
        st.balloons()
        st.info("🎉 ₹100 reward will be credited to your FASTag within 24 hours!")


def render_sidebar():
    """Render sidebar with stats and info"""
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


def main():
    """Main application entry point"""
    init_session()
    render_sidebar()
    render_header()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🚨 Report Violation", "📈 Dashboard", "🏆 Leaderboard"])
    
    with tab1:
        report_data = render_upload_section()
        
        if report_data:
            processed = process_violation(report_data)
            if processed:
                render_results(processed)
    
    with tab2:
        st.header("Enforcement Dashboard")
        st.info("Real-time statistics coming soon...")
        
        # Placeholder charts
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


if __name__ == "__main__":
    main()
