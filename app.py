# admin_app.py
# Rooted World Tour - Admin / Staff Application
# (Registration moved to separate app)

import streamlit as st
import pandas as pd
from datetime import datetime
import io
import urllib.parse
import re
import os
import tempfile
import shutil

# ── QR Scanning imports ──────────────────────────────────────────────────
try:
    import cv2
    import numpy as np
    BARCODE_SCANNING_AVAILABLE = True
except ImportError:
    BARCODE_SCANNING_AVAILABLE = False
    cv2 = None
    np = None

# ── Google Drive imports ─────────────────────────────────────────────────
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.auth.transport.requests import Request
    import pickle
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

# ── Your custom modules ──────────────────────────────────────────────────
from database import EventDatabase
from barcode_generator import BarcodeGenerator
from utils import create_dashboard_charts, format_phone, create_sidebar
from drive_handler import GoogleDriveManager  # assuming GoogleDriveManager is here

# Page configuration
st.set_page_config(
    page_title="Rooted World Tour - Admin & Check-in",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session state initialization ─────────────────────────────────────────
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

# ── Auto-checkin from URL ─────────────────────────────────────────────────
query_params = st.query_params
if 'ticket' in query_params and 'action' in query_params:
    ticket_id = query_params['ticket'][0] if isinstance(query_params['ticket'], list) else query_params['ticket']
    action = query_params['action'][0] if isinstance(query_params['action'], list) else query_params['action']
   
    if action == 'checkin':
        st.query_params.clear()
        with st.spinner(f"Checking in ticket {ticket_id}..."):
            success, attendee = st.session_state.db.quick_checkin(ticket_id)
            if success:
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
                        Enjoy the Worship Court Lagos!<br>
                        Please proceed to the main auditorium.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                st.balloons()
                st.markdown("""
                <script>
                    setTimeout(function() { window.location.href = "/"; }, 5000);
                </script>
                """, unsafe_allow_html=True)
                st.stop()
            else:
                st.error(f"❌ Ticket {ticket_id} not found or already checked in")

# ── Sidebar ───────────────────────────────────────────────────────────────
selected_page = create_sidebar()

if selected_page != st.session_state.page:
    st.session_state.page = selected_page

# ── HOME PAGE ─────────────────────────────────────────────────────────────
if st.session_state.page == "Home":
    st.markdown("""
    <div class="main-header">
        <h1>ROOTED WORLD TOUR</h1>
        <h2>Worship Court Lagos • MOBILE REGISTRATION SYSTEM</h2>
    </div>
    """, unsafe_allow_html=True)

    st.info("""
    🚀 **MOBILE-FIRST REGISTRATION** — Attendees scan the QR below to register on their phones.
    """)

    # Quick Actions (no New Registration)
    st.subheader("🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ QR Code Check-in", use_container_width=True):
            st.session_state.page = "Check-in"
            st.rerun()
    with col2:
        if st.button("📊 View Dashboard", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()
    with col3:
        if st.button("🎫 Manage Tickets", use_container_width=True):
            st.session_state.page = "Manage"
            st.rerun()

    # Stats Overview
    st.subheader("📈 Live Event Statistics")
    stats = st.session_state.db.get_dashboard_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Registered", stats.get('total', 0))
    with col2:
        st.metric("Checked In", stats.get('checked_in', 0))
    with col3:
        st.metric("Check-in Rate", stats.get('checkin_rate', '0%'))
    with col4:
        st.metric("Pending Check-in", stats.get('pending', 0))

    # Recent Activity (placeholder - replace with real data later)
    st.subheader("🕐 Recent Registrations")
    st.markdown("""
    <div style="background: #1a1a2e; padding: 1rem; border-radius: 10px;">
        <table style="width: 100%; color: white; border-collapse: collapse;">
            <tr><th>Ticket ID</th><th>Name</th><th>Status</th><th>Time</th></tr>
            <tr><td>RWT-ABC123</td><td>John Doe</td><td>Checked In</td><td>08:30 PM</td></tr>
            <!-- add more rows as needed -->
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Mobile Registration QR (single block)
    st.subheader("📱 Mobile Registration QR – Scan to Register")
    REGISTRATION_APP_URL = "https://worship-court-4ygkqctcw64shjludxserw.streamlit.app/"

    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(REGISTRATION_APP_URL)
        qr.make(fit=True)
        registration_qr = qr.make_image(fill_color="black", back_color="white")
    except ImportError:
        registration_qr = st.session_state.barcode_gen.create_registration_qr()
        st.caption("Tip: install `qrcode[pil]` for real link QR code")

    st.markdown('<div class="qr-container" style="max-width: 320px; margin: 0 auto;">', unsafe_allow_html=True)
    st.image(registration_qr, caption="Scan with phone camera to register")
    st.markdown('</div>', unsafe_allow_html=True)

    qr_buffer = io.BytesIO()
    registration_qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    st.download_button(
        label="📥 Download this QR Code",
        data=qr_buffer,
        file_name="rooted_registration_qr.png",
        mime="image/png"
    )

    st.markdown("""
    ### How it works for attendees
    1. Scan the QR above with phone camera  
    2. Fill the registration form  
    3. Download & save their personal check-in QR ticket  
    4. Show it at the event entrance
    """)

# ── CHECK-IN PAGE ─────────────────────────────────────────────────────────
elif st.session_state.page == "Check-in":
    st.title("✅ QR Code Check-in System")
    # ... paste the full original Check-in page code here (tabs, scanning, etc.) ...

# ── DASHBOARD, MANAGE, EXPORT, FOOTER ─────────────────────────────────────
# Paste the rest of your original pages here (Dashboard, Manage, Export, footer)
# Make sure they are at the same indentation level as the Home and Check-in blocks

# Example footer (adjust as needed)
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em; padding: 20px 0;">
    <p><strong>Rooted World Tour Registration System • Admin View</strong></p>
    <p>For support: tech@rootedworldtour.com</p>
</div>
""", unsafe_allow_html=True)
