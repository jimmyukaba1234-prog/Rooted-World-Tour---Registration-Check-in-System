import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

def create_dashboard_charts(stats, df):
    """Create comprehensive dashboard charts"""
    
    charts = {}
    
    # 1. Registration vs Check-in Gauge
    if stats['total'] > 0:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = stats['checked_in'],
            title = {'text': f"Check-ins: {stats['checked_in']}/{stats['total']}"},
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [None, stats['total']]},
                'bar': {'color': "#4CAF50"},
                'steps': [
                    {'range': [0, stats['total']], 'color': "lightgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': stats['total']
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        charts['checkin_gauge'] = fig_gauge
    
    # 2. Hourly Check-in Chart
    if stats.get('hourly_checkins'):
        hours = list(stats['hourly_checkins'].keys())
        counts = list(stats['hourly_checkins'].values())
        
        fig_hourly = go.Figure(data=[
            go.Bar(x=hours, y=counts, marker_color='#4CAF50')
        ])
        fig_hourly.update_layout(
            title="Check-ins by Hour (Today)",
            xaxis_title="Hour",
            yaxis_title="Number of Check-ins",
            height=300
        )
        charts['hourly_chart'] = fig_hourly
    
    # 3. Registration Source (if available)
    if 'source_system' in df.columns:
        source_counts = df['source_system'].value_counts().reset_index()
        source_counts.columns = ['source', 'count']
        
        fig_sources = px.pie(source_counts, values='count', names='source',
                           title='Registration Sources',
                           color_discrete_sequence=px.colors.sequential.Greens)
        fig_sources.update_traces(textposition='inside', textinfo='percent+label')
        charts['sources_chart'] = fig_sources
    
    # 4. Registration Timeline
    if 'registration_time' in df.columns and not df.empty:
        df_copy = df.copy()
        df_copy['date'] = pd.to_datetime(df_copy['registration_time']).dt.date
        daily_counts = df_copy.groupby('date').size().reset_index(name='count')
        
        fig_timeline = px.area(daily_counts, x='date', y='count',
                             title='Registration Timeline',
                             color_discrete_sequence=['#4CAF50'])
        fig_timeline.update_layout(
            xaxis_title="Date",
            yaxis_title="Registrations",
            height=300
        )
        charts['timeline_chart'] = fig_timeline
    
    # 5. Status Distribution
    if 'status' in df.columns:
        status_counts = df['status'].value_counts().reset_index()
        status_counts.columns = ['status', 'count']
        
        fig_status = px.pie(status_counts, values='count', names='status',
                          title='Registration Status',
                          color_discrete_sequence=['#4CAF50', '#FF9800', '#2196F3'])
        fig_status.update_traces(textposition='inside', textinfo='percent+label')
        charts['status_chart'] = fig_status
    
    return charts

def create_registration_form():
    """Create the registration form with all required fields"""
    
    with st.form("registration_form", clear_on_submit=True):
        st.subheader("📝 Registration Form")
        
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name *", placeholder="John")
            last_name = st.text_input("Last Name *", placeholder="Doe")
            email = st.text_input("Email *", placeholder="john@example.com")
            phone = st.text_input("Phone Number", placeholder="(555) 123-4567")
            
        with col2:
            emergency_contact = st.text_input("Emergency Contact", 
                                            placeholder="Name & Phone")
            medical_notes = st.text_area("Medical Notes/Allergies", 
                                       placeholder="Any medical conditions we should know about",
                                       height=60)
            
            col2a, col2b = st.columns(2)
            with col2a:
                worship_team = st.checkbox("Worship Team")
            with col2b:
                volunteer = st.checkbox("Volunteer")
        
        # Terms and conditions
        st.markdown("---")
        terms = st.checkbox("I agree to the terms and conditions *")
        
        submitted = st.form_submit_button("Register for Worship Night", 
                                         type="primary", 
                                         use_container_width=True)
        
        if submitted:
            # Validate required fields
            if not all([first_name, last_name, email, terms]):
                st.error("Please fill all required fields (*)")
                return False, None
            
            # Generate scanned_data for the database
            timestamp = int(datetime.now().timestamp())
            scanned_data = f"REG_{first_name[:3].upper()}{last_name[:3].upper()}_{timestamp}"
            
            return True, {
                'first_name': first_name.strip(),
                'last_name': last_name.strip(),
                'email': email.strip(),
                'phone': phone.strip() if phone else '',
                'emergency_contact': emergency_contact.strip() if emergency_contact else '',
                'medical_notes': medical_notes.strip() if medical_notes else '',
                'worship_team': 1 if worship_team else 0,
                'volunteer': 1 if volunteer else 0,
                'scanned_data': scanned_data
            }
    
    return False, None

def format_phone(phone):
    """Format phone number consistently (supports international numbers)"""
    if not phone:
        return ""

    # Keep digits only
    digits = ''.join(filter(str.isdigit, phone))

    # Nigeria (+234) → +234 902 014 9019
    if digits.startswith("234") and len(digits) == 13:
        return f"+234 {digits[3:6]} {digits[6:9]} {digits[9:]}"

    # UK (+44) → +44 7058 866 939
    if digits.startswith("44") and len(digits) >= 12:
        return f"+44 {digits[2:6]} {digits[6:9]} {digits[9:]}"

    # US/Canada (10 digits)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    # US/Canada with country code
    if len(digits) == 11 and digits.startswith("1"):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    # Fallback: return original input
    return phone


def create_sidebar():
    """Create the sidebar navigation"""
    
    with st.sidebar:
        # Logo/Title
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: #4CAF50; margin: 0; font-size: 3rem;">🌿</h1>
            <h2 style="color: white; margin: 0; font-size: 1.8rem;">ROOTED WORLD</h2>
            <h3 style="color: #4CAF50; margin: 0; font-weight: 300; font-size: 1.2rem;">WORSHIP TOUR</h3>
            <p style="color: #888; font-size: 0.9em; margin-top: 5px;">
            HERE FOR WORSHIP • NIGHT OF ENCOUNTER
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation
        try:
            from streamlit_option_menu import option_menu
            
            selected = option_menu(
                menu_title=None,
                options=["Home", "Register", "Check-in", "Dashboard", "Manage", "Export"],
                icons=["house", "person-plus", "check-circle", "bar-chart", "gear", "download"],
                menu_icon="cast",
                default_index=0,
                styles={
                    "container": {"padding": "0!important", "background-color": "#262730"},
                    "icon": {"color": "#4CAF50", "font-size": "20px"},
                    "nav-link": {
                        "font-size": "16px", 
                        "text-align": "left", 
                        "margin": "0px",
                        "padding": "12px 16px"
                    },
                    "nav-link-selected": {
                        "background-color": "#4CAF50",
                        "font-weight": "600"
                    },
                }
            )
            
        except ImportError:
            # Fallback if option_menu is not installed
            st.warning("Install streamlit-option-menu for better navigation")
            selected = st.selectbox(
                "Navigation",
                ["Home", "Register", "Check-in", "Dashboard", "Manage", "Export"]
            )
        
        st.markdown("---")
        
        # Event Info
        st.markdown("### 📅 Current Event")
        st.info("""
        **Rooted World Tour**  
        Worship Night Encounter  
        *Saturday, 8:00 PM*  
        Main Auditorium
        """)
        
        # Quick Stats
        try:
            from database import EventDatabase
            db = EventDatabase()
            stats = db.get_dashboard_stats()
            
            st.markdown("### 📊 Quick Stats")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", stats.get('total', 0))
            with col2:
                st.metric("Checked In", stats.get('checked_in', 0))
        except:
            pass
        
        st.markdown("---")
        
        # System Status
        st.markdown("### 🔧 System Status")
        
        # Check if QR scanning is available
        try:
            import cv2
            from pyzbar.pyzbar import decode
            st.success("✅ QR Scanner: Available")
        except ImportError:
            st.warning("⚠️ QR Scanner: Install pyzbar")
        
        st.markdown("---")
        st.caption("Rooted World Tour v3.0 • Mobile Registration System")
        
        return selected

def create_checkin_interface():
    """Create check-in interface with scanning options"""
    
    st.subheader("Check-in Methods")
    
    method = st.radio(
        "Select check-in method:",
        ["QR Code Scan", "Manual Entry", "Search by Name"],
        horizontal=True
    )
    
    if method == "QR Code Scan":
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("Use webcam to scan QR code or upload image")
            
            # Webcam option
            if st.button("🎥 Use Webcam", use_container_width=True):
                st.session_state.scanning = True
            
            # Upload option
            uploaded_file = st.file_uploader(
                "Upload QR code image",
                type=['png', 'jpg', 'jpeg'],
                key="qr_upload"
            )
            
            if uploaded_file:
                # Process uploaded QR code
                st.info(f"Uploaded: {uploaded_file.name}")
        
        with col2:
            manual_id = st.text_input("Or enter Ticket ID:")
            if manual_id and st.button("Check In", key="manual_checkin", use_container_width=True):
                return manual_id
    
    elif method == "Manual Entry":
        ticket_id = st.text_input("Ticket ID:", placeholder="RWT-ABC123")
        if ticket_id and st.button("Check In", type="primary", use_container_width=True):
            return ticket_id
    
    else:  # Search by Name
        search_term = st.text_input("Search by name:", placeholder="First or last name")
        if search_term:
            st.info(f"Search results for: {search_term}")
            # This would search the database
    
    return None
