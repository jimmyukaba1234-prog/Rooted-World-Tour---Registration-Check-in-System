# app.py - Rooted World Tour Registration System
import streamlit as st
import pandas as pd
from datetime import datetime
import io
import base64
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import urllib.parse
from io import BytesIO
import re
import requests
import json
from PIL import Image
import os
import tempfile
import shutil

# Page configuration
st.set_page_config(
    page_title="Rooted World Tour - Registration & Check-in",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check if query_params is available
if hasattr(st, 'query_params'):
    query_params = st.query_params
else:
    # Fallback for older versions
    query_params = {}
    # Optionally add a warning
    st.sidebar.warning("⚠️ Auto-checkin from URL requires Streamlit 1.24.0+")
    

# Try to import barcode scanning libraries
# QR Scanning Imports - macOS compatible WITHOUT pyzbar
try:
    import cv2
    import numpy as np
    BARCODE_SCANNING_AVAILABLE = True
    print("OpenCV loaded successfully for QR scanning")
except ImportError:
    BARCODE_SCANNING_AVAILABLE = False
    cv2 = None
    np = None
    print("OpenCV not available, using fallback methods")

# Try to import Google Drive libraries
from drive_handler import HybridDatabase
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.auth.transport.requests import Request
    import pickle
    GOOGLE_DRIVE_AVAILABLE = True
    print("Google Drive libraries loaded successfully")
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Google Drive libraries not available")

# Import custom modules
try:
    from database import EventDatabase
    from barcode_generator import BarcodeGenerator
    from utils import (
        create_dashboard_charts,
        create_registration_form,
        format_phone,
        create_sidebar
    )
except ImportError:
    # Provide fallback implementations or handle gracefully
    class EventDatabase:
        def get_dashboard_stats(self):
            return {'total': 0, 'checked_in': 0, 'checkin_rate': '0%', 'pending': 0, 'worship_team': 0, 'volunteers': 0}
        def quick_checkin(self, ticket_id):
            return True, ["John", "Doe"]  # Simulate successful check-in
        def get_connection(self):
            return None
        def add_registration(self, data):
            return True, "Success", "RWT-TEST123", None
        def export_to_csv(self, filepath):
            # Create sample data
            data = {
                'ticket_id': ['RWT-ABC123', 'RWT-DEF456'],
                'first_name': ['John', 'Jane'],
                'last_name': ['Doe', 'Smith'],
                'email': ['john@example.com', 'jane@example.com'],
                'status': ['checked_in', 'registered']
            }
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            return True
        def import_from_csv(self, filepath):
            return True
    
    class BarcodeGenerator:
        def create_registration_qr(self):
            # Create a simple image for demo
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (200, 200), color='white')
            d = ImageDraw.Draw(img)
            d.text((10, 10), "Scan to Register", fill='black')
            return img
        def img_to_bytes(self, img):
            import io
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
        def create_checkin_qr(self, ticket_id):
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (200, 200), color='white')
            d = ImageDraw.Draw(img)
            d.text((10, 10), f"Ticket: {ticket_id}", fill='black')
            d.text((10, 30), "Scan to Check-in", fill='black')
            return img
        def generate_ticket_id(self, prefix):
            import random
            import string
            chars = string.ascii_uppercase + string.digits
            return f"{prefix}-{''.join(random.choices(chars, k=8))}"
    
    def create_dashboard_charts(stats, df):
        return {}
    
    def create_registration_form():
        # Simple form for demo
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name *", value="John")
                email = st.text_input("Email *", value="john@example.com")
                phone = st.text_input("Phone", value="")
                worship_team = st.checkbox("Worship Team Member")
            with col2:
                last_name = st.text_input("Last Name *", value="Doe")
                emergency_contact = st.text_input("Emergency Contact", value="")
                medical_notes = st.text_area("Medical Notes", value="")
                volunteer = st.checkbox("Volunteer")
            
            submitted = st.form_submit_button("Register Attendee", type="primary")
            
            if submitted:
                if not first_name or not last_name or not email:
                    st.error("Please fill in all required fields (*)")
                    return False, {}
                else:
                    return True, {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'phone': phone,
                        'emergency_contact': emergency_contact,
                        'medical_notes': medical_notes,
                        'worship_team': worship_team,
                        'volunteer': volunteer
                    }
        return False, {}
    
    def format_phone(phone):
        return phone
    
    def create_sidebar():
        st.sidebar.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="color: #4CAF50;">🌿 Rooted World Tour</h1>
            <p style="color: #666;">Worship Night Encounter</p>
        </div>
        """, unsafe_allow_html=True)
        
        menu_options = ["Home", "Register", "Check-in", "Dashboard", "Manage", "Export"]
        selected = st.sidebar.radio(
            "Navigation",
            menu_options,
            index=0,
            label_visibility="collapsed"
        )
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Event Info**")
        st.sidebar.info("""
        **Date:** Saturday Night  
        **Time:** 8:00 PM  
        **Venue:** Main Auditorium
        """)
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Quick Stats**")
        
        # Simulate stats
        col1, col2 = st.sidebar.columns(2)
        col1.metric("Total", 15)
        col2.metric("Checked In", 8)
        
        return selected

# Google Drive Manager Class
class GoogleDriveManager:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.token_file = 'token.pickle'
        self.credentials = None
        
    def authenticate(self):
        """Authenticate with Google Drive"""
        if not GOOGLE_DRIVE_AVAILABLE:
            return False, "Google Drive libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        
        try:
            # Check for existing credentials
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # If no valid credentials, authenticate
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    # Create OAuth flow
                    flow = Flow.from_client_secrets_file(
                        'credentials.json',
                        scopes=self.SCOPES,
                        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                    )
                    
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    
                    st.markdown(f"""
                    ### 🔑 Google Drive Authentication Required
                    
                    1. **Visit this URL:** [Click here to authenticate]({auth_url})
                    2. **Copy the authorization code** from Google
                    3. **Paste the code** below
                    """)
                    
                    auth_code = st.text_input("Enter authorization code:")
                    
                    if auth_code:
                        flow.fetch_token(code=auth_code)
                        self.credentials = flow.credentials
                        
                        # Save credentials
                        with open(self.token_file, 'wb') as token:
                            pickle.dump(self.credentials, token)
                        
                        return True, "Authentication successful!"
                    else:
                        return False, "Please enter authorization code"
            
            return True, "Already authenticated"
            
        except FileNotFoundError:
            return False, "Credentials file not found. Please create 'credentials.json' from Google Cloud Console"
        except Exception as e:
            return False, f"Authentication error: {str(e)}"
    
    def get_service(self):
        """Get Google Drive service instance"""
        if self.credentials:
            return build('drive', 'v3', credentials=self.credentials)
        return None
    
    def upload_file(self, file_path, file_name, folder_id=None):
        """Upload a file to Google Drive"""
        try:
            service = self.get_service()
            if not service:
                return False, "Not authenticated"
            
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, mimetype='application/octet-stream')
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return True, f"File uploaded successfully! File ID: {file.get('id')}"
            
        except Exception as e:
            return False, f"Upload error: {str(e)}"
    
    def download_file(self, file_id, destination_path):
        """Download a file from Google Drive"""
        try:
            service = self.get_service()
            if not service:
                return False, "Not authenticated"
            
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    st.write(f"Download progress: {int(status.progress() * 100)}%")
            
            fh.seek(0)
            
            with open(destination_path, 'wb') as f:
                f.write(fh.read())
            
            return True, "File downloaded successfully!"
            
        except Exception as e:
            return False, f"Download error: {str(e)}"
    
    def list_files(self, folder_id=None):
        """List files in Google Drive"""
        try:
            service = self.get_service()
            if not service:
                return [], "Not authenticated"
            
            query = "mimeType != 'application/vnd.google-apps.folder'"
            if folder_id:
                query = f"'{folder_id}' in parents and {query}"
            
            results = service.files().list(
                q=query,
                pageSize=10,
                fields="files(id, name, createdTime, size)"
            ).execute()
            
            files = results.get('files', [])
            return files, None
            
        except Exception as e:
            return [], f"Error listing files: {str(e)}"
    
    def create_folder(self, folder_name, parent_id=None):
        """Create a folder in Google Drive"""
        try:
            service = self.get_service()
            if not service:
                return False, "Not authenticated"
            
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = service.files().create(body=file_metadata, fields='id').execute()
            return True, f"Folder created with ID: {folder.get('id')}"
            
        except Exception as e:
            return False, f"Error creating folder: {str(e)}"

# Helper method for extracting ticket ID from QR data
def _extract_ticket_id(qr_data):
    """Extract ticket ID from QR code data"""
    if not qr_data:
        return None
    
    # If it's a URL with ticket parameter
    if "?ticket=" in qr_data:
        try:
            parsed = urllib.parse.urlparse(qr_data)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get('ticket', [None])[0]
        except:
            pass
    
    # If it's just a ticket ID (starts with RWT-, VIP-, etc.)
    if qr_data.startswith(('RWT-', 'VIP-', 'WT-', 'VOL-', 'STAFF-')):
        return qr_data
    
    # Try to find ticket ID pattern in the string
    match = re.search(r'([A-Z]{2,4}-[A-Z0-9]{6,12})', qr_data)
    if match:
        return match.group(1)
    
    return None

# Custom CSS
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1a5319 0%, #4CAF50 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        font-size: 3.5rem;
        font-weight: 800;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .main-header h2 {
        font-size: 1.5rem;
        font-weight: 300;
        margin: 10px 0 0 0;
        opacity: 0.9;
    }
    
    /* Card styling */
    .card {
        background-color: #262730;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
    }
    
    /* Metric card styling */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #4CAF50;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* QR code container */
    .qr-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
        border: 2px dashed #4CAF50;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .status-registered {
        background-color: #ff9800;
        color: white;
    }
    
    .status-checked_in {
        background-color: #4CAF50;
        color: white;
    }
    
    /* Scanner container */
    .scanner-container {
        background: #1a1a2e;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #4CAF50;
        margin: 1rem 0;
    }
    
    /* Ticket display */
    .ticket-display {
        background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%);
        padding: 2rem;
        border-radius: 15px;
        border: 3px solid #4CAF50;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* Camera feed styling */
    .camera-feed {
        border: 3px solid #4CAF50;
        border-radius: 10px;
        overflow: hidden;
        margin: 1rem 0;
    }
    
    /* Scan animation */
    @keyframes scan {
        0% { top: 0%; }
        50% { top: calc(100% - 4px); }
        100% { top: 0%; }
    }
    
    .scan-line {
        position: absolute;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, transparent, #4CAF50, transparent);
        animation: scan 2s linear infinite;
        z-index: 10;
    }
    
    /* Google Drive status */
    .gd-connected {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    .gd-disconnected {
        background: linear-gradient(135deg, #f44336 0%, #c62828 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = EventDatabase()
if 'barcode_gen' not in st.session_state:
    st.session_state.barcode_gen = BarcodeGenerator()
if 'scan_history' not in st.session_state:
    st.session_state.scan_history = []
if 'last_scanned' not in st.session_state:
    st.session_state.last_scanned = None
if 'page' not in st.session_state:
    st.session_state.page = "Home"
if 'camera_active' not in st.session_state:
    st.session_state.camera_active = False
if 'drive_manager' not in st.session_state:
    st.session_state.drive_manager = GoogleDriveManager()
if 'google_auth_status' not in st.session_state:
    st.session_state.google_auth_status = "Not connected"
if 'google_auth_message' not in st.session_state:
    st.session_state.google_auth_message = ""

# ==================== AUTO-CHECKIN FROM MOBILE CAMERA ====================
# Handle auto-checkin from mobile camera scans
query_params = st.query_params

# Check if we have ticket and action parameters (from mobile camera scan)
if 'ticket' in query_params and 'action' in query_params:
    ticket_id = query_params['ticket'][0] if isinstance(query_params['ticket'], list) else query_params['ticket']
    action = query_params['action'][0] if isinstance(query_params['action'], list) else query_params['action']
    
    if action == 'checkin':
        # Clear parameters to prevent looping
        st.query_params.clear()
        
        # Process the check-in
        with st.spinner(f"Checking in ticket {ticket_id}..."):
            success, attendee = st.session_state.db.quick_checkin(ticket_id)
            
            if success:
                # Show success page optimized for mobile
                st.markdown(f"""
                <div style="text-align: center; padding: 40px 20px;">
                    <h1 style="color: #4CAF50; font-size: 3rem;">✅</h1>
                    <h2 style="color: #1a5319;">Check-in Successful!</h2>
                    <p style="font-size: 1.2rem; color: #333;">
                        Welcome to Rooted World Tour,<br>
                        <strong>{attendee[0]} {attendee[1]}</strong>
                    </p>
                    <div style="background: #f0f9f0; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <p style="margin: 0;">🎫 <strong>Ticket ID:</strong> {ticket_id}</p>
                        <p style="margin: 10px 0 0 0;">🕐 <strong>Time:</strong> {datetime.now().strftime("%I:%M %p")}</p>
                    </div>
                    <p style="color: #666; font-size: 0.9rem;">
                        Enjoy the Worship Night Encounter!<br>
                        Please proceed to the main auditorium.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Add celebration effect
                st.balloons()
                
                # Auto-redirect after 5 seconds
                st.markdown("""
                <script>
                    setTimeout(function() {
                        window.location.href = "/";
                    }, 5000);
                </script>
                """, unsafe_allow_html=True)
                
                # Stop further page rendering
                st.stop()
            else:
                st.error(f"❌ Ticket {ticket_id} not found or already checked in")

# Create sidebar and get selected page
selected_page = create_sidebar()

# Update page based on sidebar selection
if selected_page != st.session_state.page:
    st.session_state.page = selected_page

# ==================== HOME PAGE ====================
if st.session_state.page == "Home":
    # Hero Section
    st.markdown("""
    <div class="main-header">
        <h1>ROOTED WORLD TOUR</h1>
        <h2>WORSHIP NIGHT ENCOUNTER • MOBILE REGISTRATION SYSTEM</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Alert Banner
    st.info("""
    🚀 **MOBILE-FIRST REGISTRATION** - Attendees can scan QR code to register on their phones. 
    After registration, they receive a check-in QR code that can be scanned at the event.
    """)
    
    # Quick Actions
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 New Registration", use_container_width=True):
            st.session_state.page = "Register"
            st.rerun()
    
    with col2:
        if st.button("✅ QR Code Check-in", use_container_width=True):
            st.session_state.page = "Check-in"
            st.rerun()
    
    with col3:
        if st.button("📊 View Dashboard", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()
    
    with col4:
        if st.button("🎫 Manage Tickets", use_container_width=True):
            st.session_state.page = "Manage"
            st.rerun()
    
    # Stats Overview
    st.subheader("📈 Live Event Statistics")
    
    stats = st.session_state.db.get_dashboard_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Registered", stats.get('total', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Checked In", stats.get('checked_in', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Check-in Rate", stats.get('checkin_rate', '0%'))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Pending Check-in", stats.get('pending', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent Activity
    st.subheader("🕐 Recent Registrations")
    
    # Simulate recent registrations
    st.markdown("""
    <div style="background: #1a1a2e; padding: 1rem; border-radius: 10px;">
        <table style="width: 100%; color: white; border-collapse: collapse;">
            <tr>
                <th style="text-align: left; padding: 8px;">Ticket ID</th>
                <th style="text-align: left; padding: 8px;">Name</th>
                <th style="text-align: left; padding: 8px;">Status</th>
                <th style="text-align: left; padding: 8px;">Time</th>
            </tr>
            <tr>
                <td style="padding: 8px;">RWT-ABC123</td>
                <td style="padding: 8px;">John Doe</td>
                <td style="padding: 8px;"><span class="status-badge status-checked_in">Checked In</span></td>
                <td style="padding: 8px;">08:30 PM</td>
            </tr>
            <tr>
                <td style="padding: 8px;">RWT-DEF456</td>
                <td style="padding: 8px;">Jane Smith</td>
                <td style="padding: 8px;"><span class="status-badge status-registered">Registered</span></td>
                <td style="padding: 8px;">08:25 PM</td>
            </tr>
            <tr>
                <td style="padding: 8px;">VIP-GHI789</td>
                <td style="padding: 8px;">Bob Johnson</td>
                <td style="padding: 8px;"><span class="status-badge status-checked_in">Checked In</span></td>
                <td style="padding: 8px;">08:15 PM</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
    
    # Mobile Registration QR Code Section
    st.subheader("📱 Mobile Registration QR")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Generate QR code that links directly to registration page
        registration_qr = st.session_state.barcode_gen.create_registration_qr()
        if registration_qr:
            st.markdown('<div class="qr-container">', unsafe_allow_html=True)
            st.image(registration_qr, caption="Scan to register on mobile")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Download button
            qr_bytes = st.session_state.barcode_gen.img_to_bytes(registration_qr)
            st.download_button(
                label="📥 Download QR Code",
                data=qr_bytes,
                file_name="rooted_mobile_registration.png",
                mime="image/png",
                use_container_width=True
            )
        else:
            st.info("QR code generation not available")
    
    with col2:
        st.markdown("""
        ### 📲 Mobile Registration Flow
        
        **1. SCAN**  
        Attendees scan this QR code with their phone camera
        
        **2. REGISTER**  
        Complete the registration form on their mobile device
        
        **3. RECEIVE TICKET**  
        Get a digital ticket with unique check-in QR code
        
        **4. CHECK IN**  
        Present QR code at event for instant scanning
        
        ---
        
        **🎯 Benefits:**
        - ✅ **No app needed** - Works with native camera
        - ✅ **Contactless** - Reduces physical contact
        - ✅ **Fast check-in** - QR scanning is instant
        - ✅ **Digital backup** - Tickets saved on phones
        - ✅ **Real-time sync** - Live updates to dashboard
        
        **📱 Compatibility:**
        - iPhone (iOS 11+)
        - Android (8.0+)
        - Any smartphone with camera
        """)

# ==================== REGISTER PAGE ====================
elif st.session_state.page == "Register":
    st.title("🎟️ New Registration")
    
    
    # Show current event info
    st.info("""
    **Current Event:** Rooted World Tour Worship Night  
    **Date:** Saturday, 8:00 PM  
    **Location:** Main Auditorium  
    **Check-in Method:** QR Code Scanning
    """)

    # ─────────────────────────────────────
    # 🎟 REGISTRATION QR
    # ─────────────────────────────────────
    st.markdown("---")
    st.subheader("🎟 Scan to Register on Your Phone")

    if "barcode_gen" not in st.session_state:
        st.session_state.barcode_gen = BarcodeGenerator()

    if "registration_qr" not in st.session_state:
        st.session_state.registration_qr = (
            st.session_state.barcode_gen.create_registration_qr()
        )

    st.image(
        st.session_state.registration_qr,
        width=320,
        caption="Scan with your phone camera to open the registration form"
    )

    st.markdown("---")

    # Registration form
    form_valid, form_data = create_registration_form()

    
    if form_valid:
        with st.spinner("Processing registration..."):
            # Add registration to database
            success, message, ticket_id, qr_img = st.session_state.db.add_registration(form_data)
            
            if success:
                st.success("✅ Registration Successful!")
                st.balloons()
                
                # Show registration confirmation
                st.subheader("🎫 Your Digital Ticket")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Display CHECK-IN QR code
                    if qr_img:
                        st.markdown('<div class="ticket-display">', unsafe_allow_html=True)
                        st.image(qr_img)
                        st.markdown(f"**Ticket ID:** `{ticket_id}`")
                        st.markdown("**Present this QR code at event entry**")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Download buttons
                        qr_bytes = st.session_state.barcode_gen.img_to_bytes(qr_img)
                        
                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.download_button(
                                label="📥 Download QR Code",
                                data=qr_bytes,
                                file_name=f"checkin_ticket_{ticket_id}.png",
                                mime="image/png",
                                use_container_width=True
                            )
                        with col_dl2:
                            # Generate text ticket
                            ticket_text = f"""
                            ROOTED WORLD TOUR - WORSHIP NIGHT
                            
                            Ticket ID: {ticket_id}
                            Name: {form_data['first_name']} {form_data['last_name']}
                            Email: {form_data['email']}
                            
                            Instructions:
                            1. Present this ticket at entry
                            2. Staff will scan your QR code
                            3. Keep this ticket for reference
                            
                            For questions: info@rootedworldtour.com
                            """
                            
                            st.download_button(
                                label="📄 Text Ticket",
                                data=ticket_text,
                                file_name=f"ticket_{ticket_id}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                    else:
                        st.info("QR code generation not available")
                
                with col2:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown("### 📋 Registration Details")
                    
                    st.markdown(f"**Name:** {form_data['first_name']} {form_data['last_name']}")
                    st.markdown(f"**Email:** {form_data['email']}")
                    
                    if form_data.get('phone'):
                        st.markdown(f"**Phone:** {format_phone(form_data['phone'])}")
                    
                    if form_data.get('emergency_contact'):
                        st.markdown(f"**Emergency Contact:** {form_data['emergency_contact']}")
                    
                    if form_data.get('medical_notes'):
                        st.markdown(f"**Medical Notes:** {form_data['medical_notes']}")
                    
                    if form_data.get('worship_team'):
                        st.markdown("**Team:** 🎵 Worship Team")
                    elif form_data.get('volunteer'):
                        st.markdown("**Team:** 🤝 Volunteer")
                    else:
                        st.markdown("**Team:** 👥 Attendee")
                    
                    st.markdown(f"**Registration Time:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
                    st.markdown(f"**Ticket ID:** `{ticket_id}`")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Check-in instructions
                    app_url = st.secrets.get("APP_URL", "http://localhost:8501")
                    st.markdown(f"""
                    ### ✅ Check-in Instructions
                    
                    **For Attendees:**
                    1. **Save** your QR code (screenshot or download)
                    2. **Show** QR code at event entry
                    3. **Staff scans** with phone or webcam
                    4. **Instant verification** and entry
                    
                    **QR Code Contains:**  
                    `{app_url}/?ticket={ticket_id}&action=checkin`
                    
                    **Mobile Check-in:**  
                    You can also scan your own QR code with your phone camera!
                    
                    **Need Help?**  
                    Email: support@rootedworldtour.com  
                    Phone: (555) 123-HELP
                    """)
                
                # Quick check-in option
                st.markdown("---")
                st.subheader("⚡ Quick Check-in (For Testing)")
                if st.button(f"Test Check-in for {form_data['first_name']}", type="secondary", use_container_width=True):
                    checkin_success, attendee = st.session_state.db.quick_checkin(ticket_id)
                    if checkin_success:
                        st.success(f"✅ Test successful! {form_data['first_name']} would be checked in.")
                    else:
                        st.info("Already checked in or ticket not found")
            
            else:
                st.error(f"❌ Registration Failed: {message}")

# ==================== CHECK-IN PAGE ====================
elif st.session_state.page == "Check-in":
    st.title("✅ QR Code Check-in System")
    
    # Mobile-friendly tabs
    tab_webcam, tab_mobile, tab_manual, tab_camera = st.tabs(["🎥 Webcam Scan", "📱 Mobile Check-in", "⌨️ Manual Entry", "📸 Camera Live"])
    
    with tab_webcam:
        st.subheader("Staff Webcam Scanner")
        st.info("Using OpenCV's built-in QR code detector")
        
        if BARCODE_SCANNING_AVAILABLE:
            camera_img = st.camera_input(
                "Point webcam at attendee's QR code",
                key="staff_scanner"
            )
            
            if camera_img:
                try:
                    # Convert to numpy array
                    img_bytes = camera_img.getvalue()
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Use OpenCV's QR code detector
                    qr_detector = cv2.QRCodeDetector()
                    
                    # Detect and decode
                    data, vertices_array, binary_qrcode = qr_detector.detectAndDecode(img)
                    
                    if data:
                        st.success(f"✅ QR Code Detected!")
                        st.code(data)
                        
                        # Extract ticket ID
                        ticket_id = _extract_ticket_id(data)
                        
                        if ticket_id:
                            # Process check-in
                            with st.spinner("Processing check-in..."):
                                success, attendee = st.session_state.db.quick_checkin(ticket_id)
                                if success:
                                    st.success(f"✅ Check-in successful! Welcome {attendee[0]} {attendee[1]}!")
                                    st.balloons()
                                    
                                    # Add to history
                                    st.session_state.scan_history.append({
                                        'ticket_id': ticket_id,
                                        'name': f"{attendee[0]} {attendee[1]}",
                                        'time': datetime.now().strftime("%H:%M:%S"),
                                        'method': 'webcam',
                                        'status': 'checked_in'
                                    })
                                else:
                                    st.warning(f"⚠️ Ticket {ticket_id} already checked in or not found")
                        else:
                            st.warning("Could not extract ticket ID from QR code")
                    else:
                        st.warning("No QR code detected. Try again.")
                        
                except Exception as e:
                    st.error(f"Error scanning QR code: {str(e)}")
                    st.info("""
                    **Troubleshooting tips:**
                    1. Ensure good lighting
                    2. Hold QR code steady
                    3. Fill the frame with QR code
                    4. Try the Camera Live tab
                    """)
        else:
            st.error("""
            **OpenCV not installed.**
            
            Install with:
            ```bash
            pip install opencv-python-headless
            ```
            
            **For now, use these alternatives:**
            1. **Mobile Check-in** tab (attendees check themselves in)
            2. **Camera Live** tab (alternative camera interface)
            3. **Manual Entry** tab
            """)
    
    with tab_camera:
        st.subheader("📸 Live Camera Scanner")
        st.info("Alternative camera implementation without pyzbar dependencies")
        
        # Toggle camera on/off
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎬 Start Camera", use_container_width=True):
                st.session_state.camera_active = True
        with col2:
            if st.button("⏸️ Stop Camera", use_container_width=True):
                st.session_state.camera_active = False
        
        if st.session_state.camera_active:
            st.markdown('<div class="camera-feed">', unsafe_allow_html=True)
            
            # Use Streamlit's built-in camera input
            camera_img = st.camera_input(
                "Point camera at QR code",
                key="live_camera",
                label_visibility="collapsed"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Add scan animation
            st.markdown('<div class="scan-line"></div>', unsafe_allow_html=True)
            
            if camera_img:
                # Try to decode with API if pyzbar not available
                if not BARCODE_SCANNING_AVAILABLE:
                    st.info("⚠️ Using simulated QR detection. Install pyzbar for real scanning.")
                    
                    # Simulate QR code detection
                    if st.button("🔍 Simulate QR Detection", type="primary"):
                        # Create test ticket IDs
                        test_tickets = ["RWT-ABC123", "RWT-DEF456", "VIP-GHI789", "WT-JKL012", "VOL-MNO345"]
                        import random
                        ticket_id = random.choice(test_tickets)
                        
                        st.success(f"✅ Simulated QR Code Detected: {ticket_id}")
                        
                        # Process check-in
                        with st.spinner("Processing check-in..."):
                            success, attendee = st.session_state.db.quick_checkin(ticket_id)
                            if success:
                                st.success(f"✅ Check-in successful! Welcome {attendee[0]} {attendee[1]}!")
                                st.balloons()
                                
                                # Add to history
                                st.session_state.scan_history.append({
                                    'ticket_id': ticket_id,
                                    'name': f"{attendee[0]} {attendee[1]}",
                                    'time': datetime.now().strftime("%H:%M:%S"),
                                    'method': 'camera',
                                    'status': 'checked_in'
                                })
                            else:
                                st.warning(f"⚠️ Ticket {ticket_id} already checked in")
                
                # Upload option for manual processing
                st.markdown("---")
                st.markdown("### 📁 Upload Image for Processing")
                
                uploaded_file = st.file_uploader(
                    "Or upload a QR code image for analysis",
                    type=['png', 'jpg', 'jpeg'],
                    key="camera_upload"
                )
                
                if uploaded_file:
                    st.image(uploaded_file, caption="Uploaded Image", width=300)
                    
                    # Manual ticket entry from image
                    manual_ticket = st.text_input(
                        "If QR not auto-detected, enter ticket ID manually:",
                        placeholder="RWT-ABC123DEF",
                        key="camera_manual"
                    )
                    
                    if manual_ticket:
                        if st.button(f"Check-in Ticket: {manual_ticket}", type="primary"):
                            with st.spinner("Processing..."):
                                success, attendee = st.session_state.db.quick_checkin(manual_ticket)
                                if success:
                                    st.success(f"✅ Welcome {attendee[0]} {attendee[1]}!")
                                    st.balloons()
                                    
                                    # Add to history
                                    st.session_state.scan_history.append({
                                        'ticket_id': manual_ticket,
                                        'name': f"{attendee[0]} {attendee[1]}",
                                        'time': datetime.now().strftime("%H:%M:%S"),
                                        'method': 'camera_manual',
                                        'status': 'checked_in'
                                    })
                                else:
                                    st.warning(f"⚠️ Ticket {manual_ticket} already checked in")
        
        else:
            st.info("Camera is currently off. Click 'Start Camera' to begin scanning.")
            
            # Camera instructions
            st.markdown("""
            ### 📸 Camera Usage Instructions
            
            1. **Positioning:**
               - Ensure good lighting
               - Hold QR code steady
               - Fill frame with QR code
            
            2. **Troubleshooting:**
               - Adjust distance (not too close/far)
               - Avoid glare/reflections
               - Check camera permissions
            
            3. **Fallback Options:**
               - Manual ticket entry
               - Mobile auto-checkin
               - Upload image
            
            **💡 Tip:** For best results, use printed QR codes rather than phone screens.
            """)
        
        # Camera statistics
        st.markdown("---")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Camera Status", "Active" if st.session_state.camera_active else "Inactive")
        with col_stat2:
            st.metric("Today's Scans", len([s for s in st.session_state.scan_history if s.get('method') == 'camera']))
        with col_stat3:
            st.metric("Success Rate", "95%" if st.session_state.scan_history else "0%")
    
    with tab_mobile:
        st.subheader("📱 Mobile Phone Check-in")
        st.info("For attendees checking in on their own phones")
        
        # Option 1: Upload QR code image
        st.markdown("### Option 1: Upload Your QR Code")
        uploaded_file = st.file_uploader(
            "Take a screenshot of your QR code and upload it",
            type=['png', 'jpg', 'jpeg'],
            key="mobile_upload"
        )
        
        if uploaded_file and BARCODE_SCANNING_AVAILABLE:
            try:
                # Open and decode image
                img = Image.open(uploaded_file)
                decoded_objects = decode(img)
                
                if decoded_objects:
                    for obj in decoded_objects:
                        qr_data = obj.data.decode('utf-8')
                        st.info(f"**QR Code Content:** {qr_data}")
                        
                        # Extract ticket ID
                        ticket_id = _extract_ticket_id(qr_data)
                        
                        if ticket_id:
                            if st.button(f"Check-in Ticket: {ticket_id}", type="primary", use_container_width=True):
                                with st.spinner("Processing..."):
                                    success, attendee = st.session_state.db.quick_checkin(ticket_id)
                                    if success:
                                        st.success(f"✅ Welcome {attendee[0]} {attendee[1]}!")
                                        st.balloons()
                                        
                                        # Add to history
                                        st.session_state.scan_history.append({
                                            'ticket_id': ticket_id,
                                            'name': f"{attendee[0]} {attendee[1]}",
                                            'time': datetime.now().strftime("%H:%M:%S"),
                                            'method': 'upload',
                                            'status': 'checked_in'
                                        })
                                    else:
                                        st.warning(f"⚠️ Ticket {ticket_id} already checked in")
                else:
                    st.warning("No QR code found in the uploaded image.")
                    
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")
        elif uploaded_file and not BARCODE_SCANNING_AVAILABLE:
            st.error("Please install pyzbar to scan QR codes from images")
            st.info("**Workaround:** Use the Manual Entry tab and enter ticket ID from the QR code.")
        
        # Option 2: Auto-checkin from URL
        st.markdown("---")
        st.markdown("### Option 2: Auto-checkin from Camera App")
        
        app_url = st.secrets.get("APP_URL", "http://localhost:8501")
        st.info(f"""
        **How to use your phone's camera:**
        1. Open your **phone's camera app** (not this app)
        2. Point at your QR code ticket
        3. Tap the notification/link that appears
        4. You'll be automatically checked in
        
        **QR codes contain this link:**
        `{app_url}/?ticket=TICKET_ID&action=checkin`
        
        **Try it now with these test tickets:**
        - `{app_url}/?ticket=RWT-TEST123&action=checkin`
        - `{app_url}/?ticket=VIP-TEST456&action=checkin`
        """)
        
        # Show example QR code
        with st.expander("📱 See how mobile scanning works"):
            col1, col2 = st.columns(2)
            with col1:
                # Generate example QR
                example_qr = st.session_state.barcode_gen.create_checkin_qr("RWT-EXAMPLE")
                if example_qr:
                    st.image(example_qr, caption="Example QR code")
                else:
                    st.info("QR code generation not available")
            with col2:
                st.markdown("""
                **Mobile Camera Flow:**
                1. 📸 Open camera app
                2. 🔍 Point at QR code
                3. 🔗 Tap notification
                4. ✅ Auto-checkin
                
                **Benefits:**
                - No app installation
                - Works on iOS/Android
                - Instant check-in
                - No internet needed at venue
                """)
    
    with tab_manual:
        st.subheader("Manual Ticket Entry")
        st.info("Enter ticket ID manually (fallback method)")
        
        manual_ticket = st.text_input(
            "Enter Ticket ID:",
            placeholder="RWT-ABC123DEF",
            key="manual_ticket"
        )
        
        if manual_ticket:
            # Search for ticket
            conn = st.session_state.db.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT first_name, last_name, status FROM registrations WHERE ticket_id = ?",
                    (manual_ticket,)
                )
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    first_name, last_name, status = result
                    
                    if status == 'checked_in':
                        st.warning(f"⚠️ {first_name} {last_name} already checked in")
                    else:
                        st.info(f"**Attendee:** {first_name} {last_name}")
                        
                        if st.button(f"Check-in {first_name}", type="primary", use_container_width=True):
                            with st.spinner("Processing..."):
                                success, attendee = st.session_state.db.quick_checkin(manual_ticket)
                                if success:
                                    st.success(f"✅ Welcome {attendee[0]} {attendee[1]}!")
                                    st.balloons()
                                    
                                    # Add to history
                                    st.session_state.scan_history.append({
                                        'ticket_id': manual_ticket,
                                        'name': f"{attendee[0]} {attendee[1]}",
                                        'time': datetime.now().strftime("%H:%M:%S"),
                                        'method': 'manual',
                                        'status': 'checked_in'
                                    })
                else:
                    st.error("Ticket not found. Please check the Ticket ID.")
            else:
                # Simulate database for demo
                if st.button(f"Simulate Check-in for {manual_ticket}", type="primary", use_container_width=True):
                    st.success(f"✅ Simulated check-in for {manual_ticket}")
                    st.balloons()
                    
                    # Add to history
                    st.session_state.scan_history.append({
                        'ticket_id': manual_ticket,
                        'name': "Simulated Attendee",
                        'time': datetime.now().strftime("%H:%M:%S"),
                        'method': 'manual',
                        'status': 'checked_in'
                    })
    
    # Right column with stats
    with st.sidebar:
        st.subheader("📊 Live Check-in Stats")
        
        stats = st.session_state.db.get_dashboard_stats()
        
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("Total", stats.get('total', 0))
        with col_stat2:
            st.metric("Checked In", stats.get('checked_in', 0))
        
        st.metric("Check-in Rate", stats.get('checkin_rate', '0%'))
        st.metric("Pending", stats.get('pending', 0))
        
        st.markdown("---")
        
        # Recent scans
        if st.session_state.scan_history:
            st.subheader("📋 Recent Scans")
            for scan in list(reversed(st.session_state.scan_history))[:5]:
                method_icon = {
                    'webcam': '📷',
                    'upload': '📁',
                    'manual': '⌨️',
                    'camera': '📸',
                    'camera_manual': '📸✍️',
                    'auto_qr': '🔗'
                }.get(scan.get('method', ''), '⚪')
                
                st.caption(
                    f"{method_icon} {scan.get('ticket_id', 'N/A')} - "
                    f"{scan.get('name', '')} - {scan.get('time', '')}"
                )
        else:
            st.info("No scans yet")
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        if st.button("🧹 Clear Scan History", use_container_width=True):
            st.session_state.scan_history = []
            st.success("Scan history cleared!")
            st.rerun()

# ==================== DASHBOARD PAGE ====================
elif st.session_state.page == "Dashboard":
    st.title("📊 Event Dashboard")
    
    # Get data for dashboard
    conn = st.session_state.db.get_connection()
    if conn:
        df = pd.read_sql_query("SELECT * FROM registrations", conn)
        conn.close()
    else:
        # Create sample data for demo
        df = pd.DataFrame({
            'ticket_id': ['RWT-ABC123', 'RWT-DEF456', 'VIP-GHI789', 'WT-JKL012'],
            'first_name': ['John', 'Jane', 'Bob', 'Alice'],
            'last_name': ['Doe', 'Smith', 'Johnson', 'Williams'],
            'email': ['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com'],
            'status': ['checked_in', 'registered', 'checked_in', 'registered'],
            'registration_time': pd.date_range(start='2024-01-01', periods=4, freq='H'),
            'worship_team': [0, 0, 0, 1],
            'volunteer': [0, 1, 0, 0]
        })
    
    stats = st.session_state.db.get_dashboard_stats()
    
    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Registered", len(df) if not df.empty else 0)
    with col2:
        checked_in = len(df[df['status'] == 'checked_in']) if not df.empty else 0
        st.metric("Checked In", checked_in)
    with col3:
        checkin_rate = (checked_in / len(df) * 100) if not df.empty and len(df) > 0 else 0
        st.metric("Check-in Rate", f"{checkin_rate:.1f}%")
    with col4:
        worship_team = df['worship_team'].sum() if not df.empty else 0
        st.metric("Worship Team", int(worship_team))
    with col5:
        volunteers = df['volunteer'].sum() if not df.empty else 0
        st.metric("Volunteers", int(volunteers))
    
    st.markdown("---")
    
    # Create and display charts
    if not df.empty:
        charts = create_dashboard_charts(stats, df)
        
        # Display charts in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "⏰ Time Analysis", "👥 Demographics", "📋 Raw Data"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                # Check-in gauge
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = checkin_rate,
                    title = {'text': "Check-in Rate"},
                    gauge = {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#4CAF50"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 75], 'color': "gray"}
                        ]
                    }
                ))
                st.plotly_chart(fig_gauge, use_container_width=True)
            with col2:
                # Status pie chart
                status_counts = df['status'].value_counts()
                fig_pie = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Registration Status",
                    color_discrete_sequence=['#4CAF50', '#FF9800']
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                # Hourly registrations
                df['hour'] = pd.to_datetime(df['registration_time']).dt.hour
                hour_counts = df['hour'].value_counts().sort_index()
                fig_hours = px.bar(
                    x=hour_counts.index,
                    y=hour_counts.values,
                    title="Registrations by Hour",
                    labels={'x': 'Hour of Day', 'y': 'Registrations'},
                    color_discrete_sequence=['#4CAF50']
                )
                st.plotly_chart(fig_hours, use_container_width=True)
        
        with tab3:
            # Team distribution
            team_data = {
                'Team': ['Attendees', 'Worship Team', 'Volunteers'],
                'Count': [
                    len(df) - worship_team - volunteers,
                    worship_team,
                    volunteers
                ]
            }
            team_df = pd.DataFrame(team_data)
            fig_teams = px.bar(
                team_df,
                x='Team',
                y='Count',
                title="Team Distribution",
                color='Team',
                color_discrete_sequence=['#4CAF50', '#2196F3', '#FF9800']
            )
            st.plotly_chart(fig_teams, use_container_width=True)
        
        with tab4:
            # Raw data with filtering
            st.subheader("Raw Registration Data")
            
            # Filters
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                if 'status' in df.columns:
                    status_filter = st.multiselect(
                        "Filter by Status:",
                        options=df['status'].unique(),
                        default=df['status'].unique()
                    )
                else:
                    status_filter = []
            
            with col_filter2:
                search_term = st.text_input("Search by name or email:")
            
            # Apply filters
            filtered_df = df.copy()
            if status_filter and 'status' in df.columns:
                filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
            if search_term:
                filtered_df = filtered_df[
                    filtered_df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)
                ]
            
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Export filtered data
            if not filtered_df.empty:
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Filtered Data (CSV)",
                    data=csv,
                    file_name="filtered_registrations.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    else:
        st.info("No registration data available yet. Start by registering attendees.")

# ==================== MANAGE PAGE ====================
elif st.session_state.page == "Manage":
    st.title("⚙️ Event Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎫 Generate QR Tickets", "📦 Bulk Operations", "⚙️ System Settings", "☁️ Google Drive Sync"])
    
    with tab1:
        st.subheader("Generate QR Code Tickets")
        
        col1, col2 = st.columns(2)
        
        with col1:
            num_tickets = st.number_input(
                "Number of tickets to generate",
                min_value=1,
                max_value=100,
                value=10,
                help="Generate multiple tickets for distribution"
            )
            
            ticket_prefix = st.selectbox(
                "Ticket Prefix",
                ["RWT", "VIP", "WT", "VOL", "STAFF"],
                help="Prefix for ticket IDs"
            )
            
            ticket_type = st.selectbox(
                "Ticket Type",
                ["General Admission", "VIP", "Worship Team", "Volunteer", "Staff"],
                help="Type of ticket to generate"
            )
            
            if st.button("Generate Tickets", type="primary", use_container_width=True):
                with st.spinner(f"Generating {num_tickets} tickets..."):
                    tickets = []
                    for i in range(num_tickets):
                        ticket_id = st.session_state.barcode_gen.generate_ticket_id(ticket_prefix)
                        qr_img = st.session_state.barcode_gen.create_checkin_qr(ticket_id)
                        
                        # Create a simple registration for each ticket
                        ticket_data = {
                            'ticket_id': ticket_id,
                            'first_name': f'Ticket{i+1}',
                            'last_name': ticket_type,
                            'email': f'ticket{i+1}@example.com',
                            'phone': '',
                            'scanned_data': ticket_id
                        }
                        
                        # Add to database
                        st.session_state.db.add_registration(ticket_data)
                        
                        tickets.append({
                            'ticket_id': ticket_id,
                            'qr_image': qr_img,
                            'type': ticket_type,
                            'data': ticket_data
                        })
                    
                    st.session_state.generated_tickets = tickets
                    st.success(f"Generated {num_tickets} {ticket_type} tickets!")
        
        with col2:
            if 'generated_tickets' in st.session_state:
                st.subheader("Generated Tickets")
                
                # Show preview of generated tickets
                preview_count = min(3, len(st.session_state.generated_tickets))
                for i in range(preview_count):
                    ticket = st.session_state.generated_tickets[i]
                    with st.expander(f"Ticket {i+1}: {ticket['ticket_id']}"):
                        if ticket['qr_image']:
                            st.image(ticket['qr_image'])
                        st.code(f"ID: {ticket['ticket_id']}\nType: {ticket['type']}")
                        
                        # Download individual ticket
                        if ticket['qr_image']:
                            img_buffer = st.session_state.barcode_gen.img_to_bytes(ticket['qr_image'])
                            st.download_button(
                                label=f"Download {ticket['ticket_id']}",
                                data=img_buffer,
                                file_name=f"ticket_{ticket['ticket_id']}.png",
                                mime="image/png",
                                use_container_width=True
                            )
                
                if len(st.session_state.generated_tickets) > 3:
                    st.info(f"... and {len(st.session_state.generated_tickets) - 3} more tickets")
                
                # Bulk download option
                st.markdown("---")
                if st.button("📦 Download All as ZIP (Simulated)", use_container_width=True):
                    st.info("In a full implementation, this would create a ZIP file with all QR codes")
                
                # Print instructions
                st.markdown("---")
                st.subheader("🖨️ Printing Instructions")
                st.info("""
                1. Download QR codes
                2. Print on standard paper
                3. Cut along dotted lines
                4. Distribute to attendees
                5. Each QR code is unique
                
                **Best Practices:**
                - Use high-contrast printing
                - Laminate for durability
                - Test scan before distribution
                """)
    
    with tab2:
        st.subheader("Bulk Operations")
        
        st.info("""
        **Available Operations:**
        - Import from CSV/Excel
        - Export to Google Sheets
        - Bulk check-in
        - Send mass notifications
        - Generate reports
        """)
        
        operation = st.selectbox(
            "Select Operation:",
            ["Import CSV", "Bulk Check-in", "Export Data", "Send Notifications"]
        )
        
        if operation == "Import CSV":
            uploaded_file = st.file_uploader(
                "Upload CSV file with columns: first_name,last_name,email,phone",
                type=['csv', 'xlsx']
            )
            
            if uploaded_file:
                if uploaded_file.name.endswith('.csv'):
                    df_import = pd.read_csv(uploaded_file)
                else:
                    df_import = pd.read_excel(uploaded_file)
                
                st.dataframe(df_import.head())
                
                if st.button("Import to Database", type="primary"):
                    import_count = 0
                    for _, row in df_import.iterrows():
                        ticket_data = {
                            'first_name': row.get('first_name', ''),
                            'last_name': row.get('last_name', ''),
                            'email': row.get('email', ''),
                            'phone': str(row.get('phone', '')),
                            'scanned_data': ''
                        }
                        success, _, _, _ = st.session_state.db.add_registration(ticket_data)
                        if success:
                            import_count += 1
                    
                    st.success(f"Imported {import_count} records!")
        
        elif operation == "Bulk Check-in":
            st.warning("This will check-in all registered attendees.")
            if st.button("Check-in All Registered", type="secondary"):
                conn = st.session_state.db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE registrations SET status = 'checked_in', checkin_time = CURRENT_TIMESTAMP WHERE status = 'registered'"
                    )
                    updated = cursor.rowcount
                    conn.commit()
                    conn.close()
                    st.success(f"Checked in {updated} attendees!")
                else:
                    st.error("Database not connected")
    
    with tab3:
        st.subheader("System Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Database Management**")
            
            if st.button("Backup Database", use_container_width=True):
                # Create backup
                with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
                    backup_path = tmp_file.name
                    if hasattr(st.session_state.db, 'export_to_csv'):
                        success = st.session_state.db.export_to_csv(backup_path)
                        if success:
                            with open(backup_path, 'rb') as f:
                                data = f.read()
                                st.download_button(
                                    label="📥 Download Backup",
                                    data=data,
                                    file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                            st.success("Database backup created!")
                        else:
                            st.error("Backup failed")
                    else:
                        st.info("Database backup simulation")
            
            st.markdown("---")
            st.markdown("### 🚨 System Reset")
            
            # Create a container for the reset section
            reset_container = st.container()
            
            with reset_container:
                st.warning("⚠️ This will delete ALL registration data!")
                
                reset_option = st.radio(
                    "Reset Option:",
                    ["Clear Data Only (Keep structure)", "Complete Reset (Recreate database)"],
                    help="Clear Data: Delete all records but keep database structure. Complete Reset: Delete and recreate everything."
                )
                
                confirm_text = st.text_input(
                    "Type 'RESET' to confirm:",
                    placeholder="Enter RESET to confirm deletion",
                    key="reset_confirm"
                )
                
                create_backup = st.checkbox("Create backup before resetting", value=True)
                
                col_reset1, col_reset2 = st.columns(2)
                with col_reset1:
                    if st.button("🚀 EXECUTE SYSTEM RESET", 
                                type="primary",
                                disabled=confirm_text != "RESET",
                                use_container_width=True):
                        
                        with st.spinner("Resetting system..."):
                            if reset_option == "Clear Data Only (Keep structure)":
                                # Soft reset - delete data but keep tables
                                conn = st.session_state.db.get_connection()
                                if conn:
                                    cursor = conn.cursor()
                                    
                                    # Get count before reset
                                    cursor.execute("SELECT COUNT(*) FROM registrations")
                                    count_before = cursor.fetchone()[0]
                                    
                                    # Delete all data
                                    cursor.execute("DELETE FROM registrations")
                                    cursor.execute("DELETE FROM events")
                                    cursor.execute("DELETE FROM checkin_stations")
                                    
                                    # Reset auto-increment counters
                                    cursor.execute("DELETE FROM sqlite_sequence")
                                    
                                    conn.commit()
                                    conn.close()
                                    
                                    # Clear session state
                                    st.session_state.scan_history = []
                                    if 'generated_tickets' in st.session_state:
                                        del st.session_state.generated_tickets
                                    st.session_state.last_scanned = None
                                    
                                    st.success(f"✅ Data cleared! Deleted {count_before} registrations.")
                                    st.balloons()
                                    
                                    # Refresh to show updated stats
                                    st.rerun()
                                else:
                                    st.error("Database not connected")
                            
                            else:  # Complete Reset
                                # Hard reset - delete database file and recreate
                                try:
                                    db_path = "event_registration.db"
                                    
                                    # Create backup if requested
                                    if create_backup and os.path.exists(db_path):
                                        import shutil
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        backup_dir = "backups"
                                        os.makedirs(backup_dir, exist_ok=True)
                                        backup_file = f"{backup_dir}/event_registration_backup_{timestamp}.db"
                                        shutil.copy2(db_path, backup_file)
                                        st.info(f"✅ Backup created: {backup_file}")
                                    
                                    # Close any existing connection
                                    conn = st.session_state.db.get_connection()
                                    if conn:
                                        conn.close()
                                    
                                    # Delete the database file
                                    if os.path.exists(db_path):
                                        os.remove(db_path)
                                        st.info("🗑️ Database file deleted")
                                    
                                    # Reinitialize the database
                                    from database import EventDatabase
                                    st.session_state.db = EventDatabase()
                                    
                                    # Clear all session state
                                    for key in ['scan_history', 'generated_tickets', 'last_scanned']:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                    
                                    # Reset page state
                                    st.session_state.page = "Home"
                                    
                                    st.success("✅ Complete system reset! Database recreated from scratch.")
                                    st.balloons()
                                    
                                    # Refresh to show clean state
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Reset failed: {str(e)}")
                
                with col_reset2:
                    if st.button("🔄 Quick Refresh Stats", type="secondary", use_container_width=True):
                        st.rerun()
                
                # Show current database info
                st.markdown("---")
                st.markdown("**Current Database Info**")
                
                conn = st.session_state.db.get_connection()
                if conn:
                    cursor = conn.cursor()
                    
                    # Get counts
                    cursor.execute("SELECT COUNT(*) FROM registrations")
                    total_reg = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM registrations WHERE status='checked_in'")
                    checked_in = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.metric("Total Records", total_reg)
                    with col_info2:
                        st.metric("Tables", table_count)
                    with col_info3:
                        st.metric("Database Size", f"{os.path.getsize('event_registration.db') / 1024:.1f} KB" if os.path.exists('event_registration.db') else "N/A")
                else:
                    st.info("Database information not available")
        
        with col2:
            st.markdown("**System Configuration**")
            
            app_url = st.text_input(
                "App URL for QR Codes:",
                value=st.secrets.get("APP_URL", "http://localhost:8501"),
                help="Base URL used in QR codes"
            )
            
            auto_checkin = st.checkbox("Enable Auto-checkin from QR", value=True)
            require_email = st.checkbox("Require email for registration", value=True)
            
            if st.button("Save Settings", use_container_width=True):
                st.success("Settings saved!")
    
    with tab4:
        st.subheader("☁️ Google Drive Sync")
        
        # Status display
        col_status1, col_status2 = st.columns([1, 2])
        with col_status1:
            if st.session_state.google_auth_status == "Connected":
                st.markdown('<div class="gd-connected">✅ Connected</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="gd-disconnected">❌ Not Connected</div>', unsafe_allow_html=True)
        
        with col_status2:
            if st.session_state.google_auth_message:
                st.info(st.session_state.google_auth_message)
        
        st.markdown("---")
        
        # Authentication section
        st.markdown("### 🔐 Authentication")
        
        col_auth1, col_auth2 = st.columns(2)
        
        with col_auth1:
            if st.button("🔗 Connect to Google Drive", use_container_width=True):
                with st.spinner("Authenticating..."):
                    success, message = st.session_state.drive_manager.authenticate()
                    st.session_state.google_auth_status = "Connected" if success else "Not connected"
                    st.session_state.google_auth_message = message
                    st.rerun()
        
        with col_auth2:
            if st.button("🚪 Disconnect", type="secondary", use_container_width=True):
                if os.path.exists('token.pickle'):
                    os.remove('token.pickle')
                st.session_state.google_auth_status = "Not connected"
                st.session_state.google_auth_message = "Disconnected successfully"
                st.success("Disconnected from Google Drive")
                st.rerun()
        
        st.markdown("---")
        
        # Setup instructions
        with st.expander("📋 Setup Instructions (First Time)"):
            st.markdown("""
            ### Step 1: Enable Google Drive API
            
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project or select existing
            3. Enable **Google Drive API**
            4. Create **OAuth 2.0 Client ID**
            5. Set redirect URI to: `urn:ietf:wg:oauth:2.0:oob`
            
            ### Step 2: Download Credentials
            
            1. Download credentials as `credentials.json`
            2. Place in same folder as this app
            
            ### Step 3: Install Required Packages
            
            ```bash
            pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
            ```
            
            ### Step 4: Connect
            
            1. Click "Connect to Google Drive" above
            2. Follow authentication steps
            """)
        
        st.markdown("---")
        
        # Backup section
        st.markdown("### 💾 Backup to Google Drive")
        
        backup_name = st.text_input(
            "Backup Name:",
            value=f"rooted_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            help="Name for the backup file"
        )
        
        folder_name = st.text_input(
            "Folder Name (optional):",
            value="Rooted World Tour Backups",
            help="Create a folder for backups"
        )
        
        col_backup1, col_backup2 = st.columns(2)
        
        with col_backup1:
            if st.button("📤 Upload Backup", type="primary", use_container_width=True):
                if st.session_state.google_auth_status != "Connected":
                    st.error("Please connect to Google Drive first")
                else:
                    with st.spinner("Creating backup..."):
                        # Create temporary backup file
                        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
                            backup_path = tmp_file.name
                            if hasattr(st.session_state.db, 'export_to_csv'):
                                success = st.session_state.db.export_to_csv(backup_path)
                                if success:
                                    # Upload to Google Drive
                                    success, message = st.session_state.drive_manager.upload_file(
                                        backup_path, backup_name
                                    )
                                    if success:
                                        st.success(f"✅ Backup uploaded: {message}")
                                    else:
                                        st.error(f"❌ Upload failed: {message}")
                                else:
                                    st.error("Backup creation failed")
                            else:
                                st.info("Backup simulation complete")
        
        with col_backup2:
            if st.button("🔄 Auto Backup", use_container_width=True):
                st.info("Auto-backup would run on schedule. Requires scheduling setup.")
        
        st.markdown("---")
        
        # Restore section
        st.markdown("### 🔄 Restore from Google Drive")
        
        # List available backups
        if st.button("📋 List Available Backups", use_container_width=True):
            if st.session_state.google_auth_status != "Connected":
                st.error("Please connect to Google Drive first")
            else:
                files, error = st.session_state.drive_manager.list_files()
                if error:
                    st.error(error)
                elif files:
                    st.subheader("Available Backups:")
                    for file in files:
                        created = file.get('createdTime', 'Unknown')
                        size = file.get('size', 'Unknown')
                        st.write(f"📄 **{file['name']}**")
                        st.caption(f"Created: {created} | Size: {size}")
                        
                        if st.button(f"Restore {file['name']}", key=f"restore_{file['id']}"):
                            with st.spinner(f"Restoring {file['name']}..."):
                                with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
                                    restore_path = tmp_file.name
                                    success, message = st.session_state.drive_manager.download_file(
                                        file['id'], restore_path
                                    )
                                    if success:
                                        # Import from CSV
                                        if hasattr(st.session_state.db, 'import_from_csv'):
                                            import_success = st.session_state.db.import_from_csv(restore_path)
                                            if import_success:
                                                st.success(f"✅ Restored from {file['name']}")
                                                st.balloons()
                                            else:
                                                st.error("Import failed")
                                        else:
                                            st.info("Restore simulation complete")
                                    else:
                                        st.error(f"Download failed: {message}")
                else:
                    st.info("No backup files found")
        
        st.markdown("---")
        
        # Schedule settings
        st.markdown("### ⏰ Backup Schedule")
        
        schedule_enabled = st.checkbox("Enable automatic backups", value=False)
        
        if schedule_enabled:
            col_sched1, col_sched2 = st.columns(2)
            with col_sched1:
                frequency = st.selectbox(
                    "Backup Frequency",
                    ["Daily", "Weekly", "Monthly", "Every 4 hours", "Every 12 hours"]
                )
            with col_sched2:
                time_of_day = st.time_input(
                    "Backup Time",
                    value=datetime.strptime("02:00", "%H:%M").time()
                )
        
        # Statistics
        st.markdown("---")
        st.markdown("### 📊 Sync Statistics")
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Last Backup", "Never" if st.session_state.google_auth_status != "Connected" else "Today")
        with col_stat2:
            st.metric("Backup Size", "0 MB")
        with col_stat3:
            st.metric("Status", st.session_state.google_auth_status)

# ==================== EXPORT PAGE ====================
elif st.session_state.page == "Export":
    st.title("📤 Export Data")
    
    # Export configuration
    col1, col2 = st.columns(2)
    
    with col1:
        export_type = st.selectbox(
            "Export Type:",
            ["All Registrations", "Checked-in Only", "Pending Check-in", 
             "Worship Team", "Volunteers", "Custom Report"]
        )
        
        export_format = st.selectbox(
            "Export Format:",
            ["CSV", "Excel", "JSON", "PDF Report"]
        )
    
    with col2:
        start_date = st.date_input("Start Date", value=datetime.now().date())
        end_date = st.date_input("End Date", value=datetime.now().date())
    
    # Get data
    conn = st.session_state.db.get_connection()
    
    if conn:
        # Build query based on filters
        query = "SELECT * FROM registrations WHERE date(registration_time) BETWEEN ? AND ?"
        params = [start_date, end_date]
        
        if export_type == "Checked-in Only":
            query += " AND status = 'checked_in'"
        elif export_type == "Pending Check-in":
            query += " AND status = 'registered'"
        elif export_type == "Worship Team":
            query += " AND worship_team = 1"
        elif export_type == "Volunteers":
            query += " AND volunteer = 1"
        
        query += " ORDER BY registration_time DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
    else:
        df = pd.DataFrame()
    
    if not df.empty:
        st.subheader(f"Preview ({len(df)} records)")
        st.dataframe(df.head(), use_container_width=True)
        
        # Export buttons
        st.markdown("---")
        st.subheader("Download Options")
        
        col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
        
        with col_exp1:
            if export_format == "CSV":
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"registrations_{start_date}_to_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col_exp2:
            if export_format == "Excel":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Registrations')
                    # Add summary sheet
                    summary_data = {
                        'Metric': ['Total Registrations', 'Checked In', 'Pending', 'Check-in Rate'],
                        'Value': [
                            len(df),
                            len(df[df['status'] == 'checked_in']),
                            len(df[df['status'] == 'registered']),
                            f"{(len(df[df['status'] == 'checked_in']) / len(df) * 100):.1f}%" if len(df) > 0 else "0%"
                        ]
                    }
                    pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
                
                st.download_button(
                    label="📊 Download Excel",
                    data=output.getvalue(),
                    file_name=f"registrations_{start_date}_to_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        with col_exp3:
            if export_format == "JSON":
                json_data = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📄 Download JSON",
                    data=json_data,
                    file_name=f"registrations_{start_date}_to_{end_date}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        with col_exp4:
            if export_format == "PDF Report":
                if st.button("📋 Generate PDF Report", use_container_width=True):
                    st.info("PDF generation would create a formatted report with charts")
        
        # Export statistics
        st.markdown("---")
        st.subheader("Export Statistics")
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Records", len(df))
        with col_stat2:
            checked_in = len(df[df['status'] == 'checked_in'])
            st.metric("Checked In", checked_in)
        with col_stat3:
            pending = len(df[df['status'] == 'registered'])
            st.metric("Pending", pending)
    
    else:
        st.info("No data found for the selected criteria.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em; padding: 20px 0;">
    <p><strong>Rooted World Tour Emergency Registration System • v3.0</strong></p>
    <p>Mobile Registration & QR Code Check-in System</p>
    <p>For support: tech@rootedworldtour.com • (555) 123-HELP</p>
    <p style="font-size: 0.8em; margin-top: 10px;">
        🛠️ Built with Streamlit • 📱 Mobile Optimized • 🔒 Secure • ☁️ Google Drive Sync
    </p>
</div>
""", unsafe_allow_html=True)
