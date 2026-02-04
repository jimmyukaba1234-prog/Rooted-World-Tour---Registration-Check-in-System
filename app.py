# registration_app.py
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Rooted World Tour – Register",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Completely hide sidebar
st.markdown("""<style>
    section[data-testid="stSidebar"] { display: none !important; }
    .stApp > header { visibility: hidden; }
</style>""", unsafe_allow_html=True)

# ── Imports ──────────────────────────────────────────────────────────
try:
    from database import EventDatabase
    from barcode_generator import BarcodeGenerator
    from utils import create_registration_form, format_phone
except ImportError as e:
    st.error(f"Missing required module: {e}")
    st.stop()

# ── Initialize shared objects ────────────────────────────────────────
if 'db' not in st.session_state:
    st.session_state.db = EventDatabase()
if 'barcode_gen' not in st.session_state:
    st.session_state.barcode_gen = BarcodeGenerator()

db = st.session_state.db
barcode_gen = st.session_state.barcode_gen

# ── UI ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; padding: 2rem 1rem 1.5rem;">
    <h1 style="color: #4CAF50; margin: 0;">🌿 Rooted World Tour</h1>
    <p style="color: #555; font-size: 1.25rem; margin: 0.5rem 0 1.5rem;">
        Worship Night – Registration
    </p>
</div>
""", unsafe_allow_html=True)

st.info("Please fill in your details below. Fields marked * are required.", icon="ℹ️")

form_valid, form_data = create_registration_form()

if form_valid:
    with st.spinner("Processing your registration..."):
        success, message, ticket_id, qr_img = db.add_registration(form_data)

        if success:
            st.success("Registration completed successfully!", icon="🎉")
            st.balloons()

            st.subheader("Your Check-in Ticket")

            col_left, col_right = st.columns([1, 1.3])

            with col_left:
                if qr_img:
                    st.image(qr_img, use_column_width=True)
                    qr_bytes = barcode_gen.img_to_bytes(qr_img)
                    st.download_button(
                        "⬇️ Download QR Code",
                        data=qr_bytes,
                        file_name=f"checkin-{ticket_id}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                else:
                    st.warning("Could not generate QR image.")

            with col_right:
                st.markdown(f"**Ticket ID:** `{ticket_id}`")
                st.markdown(f"**Name:** {form_data.get('first_name','')} {form_data.get('last_name','')}")
                st.markdown(f"**Email:** {form_data.get('email','')}")
                if form_data.get('phone'):
                    st.markdown(f"**Phone:** {format_phone(form_data['phone'])}")

                role = "Attendee"
                if form_data.get('worship_team'): role = "Worship Team"
                elif form_data.get('volunteer'): role = "Volunteer"
                st.markdown(f"**Role:** {role}")

                st.caption(f"Registered • {datetime.now().strftime('%b %d, %Y   %I:%M %p')}")

            st.info("""
            **Important:**
            • Save or screenshot this QR code
            • Show it at the entrance on event day
            • Staff will scan it for quick entry
            """)

        else:
            st.error(f"Registration failed: {message}")
else:
    st.markdown("---")
    st.caption("After successful registration you will receive your personal QR code.")
