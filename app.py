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

# Page configuration
st.set_page_config(
    page_title="Rooted World Tour - Admin & Check-in",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── QR Scanning & Google Drive imports (keep as-is) ───────────────────────
try:
    import cv2
    import numpy as np
    BARCODE_SCANNING_AVAILABLE = True
except ImportError:
    BARCODE_SCANNING_AVAILABLE = False
    cv2 = None
    np = None

try:
    from google.oauth2.credentials import Credentials
    # ... (keep all your Google Drive imports)
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

# ── Custom modules ────────────────────────────────────────────────────────
try:
    from database import EventDatabase
    from barcode_generator import BarcodeGenerator
    from utils import (
        create_dashboard_charts,
        format_phone,
        create_sidebar
    )
except ImportError:
    # Your fallback classes go here (keep as in original)
    # EventDatabase, BarcodeGenerator, format_phone, create_sidebar ...
    pass  # ← paste your fallback code if needed

# ── GoogleDriveManager class (keep as-is) ────────────────────────────────
# ... paste the whole GoogleDriveManager class here ...

# ── Helper functions (keep as-is) ────────────────────────────────────────
def _extract_ticket_id(qr_data):
    # ... your original function ...

# ── Custom CSS (keep as-is) ──────────────────────────────────────────────
# ... paste your full <style> block here ...

# ── Session state initialization (keep as-is) ────────────────────────────
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

# ── Auto-checkin from URL (keep as-is) ───────────────────────────────────
query_params = st.query_params
if 'ticket' in query_params and 'action' in query_params:
    # ... your full auto-checkin success/failure page ...
    # (keep everything from here until st.stop())
    # ...

# ── Sidebar ───────────────────────────────────────────────────────────────
# IMPORTANT: We removed "Register" from the menu
def create_sidebar():
    st.sidebar.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="color: #4CAF50;">🌿 Rooted World Tour</h1>
        <p style="color: #666;">Worship Court Lagos</p>
    </div>
    """, unsafe_allow_html=True)
    
    menu_options = ["Home", "Check-in", "Dashboard", "Manage", "Export"]  # ← no Register
    selected = st.sidebar.radio(
        "Navigation",
        menu_options,
        index=0,
        label_visibility="collapsed"
    )
    
    # Rest of sidebar (event info, quick stats) - keep as is
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Event Info**")
    st.sidebar.info("""
    **Date:** Saturday Night
    **Time:** 8:00 PM
    **Venue:** Main Auditorium
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Quick Stats**")
    
    stats = st.session_state.db.get_dashboard_stats()
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Total", stats.get('total', 0))
    col2.metric("Checked In", stats.get('checked_in', 0))
    
    return selected

selected_page = create_sidebar()

if selected_page != st.session_state.page:
    st.session_state.page = selected_page

# ── HOME PAGE (updated QR) ───────────────────────────────────────────────
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
    
    # Quick Actions (no "New Registration" button anymore)
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
    
    # Stats Overview (keep as-is)
    # ... your metrics columns ...
    
    # Recent Activity (keep as-is or update to real data)
    # ... your table ...
    
    # ── Mobile Registration QR (NOW LINKS TO SEPARATE APP) ───────────────
    st.subheader("📱 Mobile Registration QR")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # IMPORTANT CHANGE HERE
        REGISTRATION_APP_URL = "https://worship-court-4ygkqctcw64shjludxserw.streamlit.app/"   # ← CHANGE THIS
        
        # Generate real QR code with the URL
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(REGISTRATION_APP_URL)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            registration_qr = img
        except ImportError:
            # fallback if qrcode not installed
            registration_qr = st.session_state.barcode_gen.create_registration_qr()
            st.caption("Install 'qrcode[pil]' for real URL QR")
        
        st.markdown('<div class="qr-container">', unsafe_allow_html=True)
        st.image(registration_qr, caption="Scan to open registration form")
        st.markdown('</div>', unsafe_allow_html=True)
        
        qr_bytes = st.session_state.barcode_gen.img_to_bytes(registration_qr)
        st.download_button(
            label="📥 Download QR Code",
            data=qr_bytes,
            file_name="rooted_mobile_registration.png",
            mime="image/png",
            use_container_width=True
        )
    
    with col2:
        # Instructions (keep as-is)
        st.markdown("""
        ### 📲 Mobile Registration Flow
        **1. SCAN** this QR code  
        **2. REGISTER** on their phone  
        **3. RECEIVE** personal check-in QR  
        **4. CHECK IN** at the event
        ...
        """)

# ── CHECK-IN PAGE (keep everything from here) ────────────────────────────
elif st.session_state.page == "Check-in":
    # ... paste your entire original Check-in page code here ...
    # including all tabs (Webcam, Mobile, Manual, Camera Live)
    # sidebar stats, scan history, etc.

# ── DASHBOARD PAGE ───────────────────────────────────────────────────────
elif st.session_state.page == "Dashboard":
    # ... your full dashboard code ...

# ── MANAGE PAGE ──────────────────────────────────────────────────────────
elif st.session_state.page == "Manage":
    # ... your full manage code ...

# ── EXPORT PAGE ──────────────────────────────────────────────────────────
elif st.session_state.page == "Export":
    # ... your full export code ...

# ── Footer (keep as-is) ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em; padding: 20px 0;">
    <p><strong>Rooted World Tour Registration System • Admin View</strong></p>
    <p>For support: tech@rootedworldtour.com</p>
</div>
""", unsafe_allow_html=True)