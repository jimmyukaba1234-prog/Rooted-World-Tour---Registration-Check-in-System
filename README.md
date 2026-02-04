# Event Registration System
website: https://worship-court-feksijgjxqemcpddzdma7h.streamlit.app/
website: https://worship-court-ew5d8shfk5zqvypkg5tyvr.streamlit.app/

A Streamlit-based backup registration system for events when the main scanning machine stops working.

## Features

- **📝 Registration**: Scan QR Code to Register attendees
- **✅ Check-in**: Check-in attendees with ticket IDs
- **📊 Real-time Dashboard**: Visualize registration trends and statistics
- **🔄 Data Merging**: Merge backup data with original system data
- **📤 Data Export**: Export to CSV or Excel formats
- **📋 Duplicate Handling**: Smart merging with backup data taking precedence

## Installation

1. Clone the repository or download the files
2. Install dependencies:
bash
pip install -r requirements.txt

# Rooted World Tour - Registration & Check-in System

Hey there! 👋

Back in late 2025, I volunteered as a data analyst for the **Rooted World Tour** worship night organized by Worship Court Lagos. During one of the planning meetings, the team casually mentioned how they had **lost a lot of important registration data** from the previous edition — names, contacts, numbers, everything just vanished. That hit me hard because I know how valuable accurate attendee data is for planning, follow-up, and measuring impact.

So I offered to build something simple but solid: a **mobile-friendly registration + check-in system** that would

- let people register easily from their phones (no app install needed)
- generate personal QR tickets instantly
- allow staff to check people in quickly (webcam scan, manual entry, or even auto-check-in from phone camera)
- show real-time stats & visualizations on the admin dashboard
- let us export clean CSV reports anytime

I built two separate Streamlit apps that **share the same SQLite database**:

1. registration_app.py → public-facing registration form (no login, no sidebar, just the form + ticket download)
2. app.py → staff/admin dashboard with check-in tools, live stats, charts, manage tickets, export, and Google Drive backup

### What actually happened

We launched the system on event day.  
**Result?** Over **2,000 people registered** successfully through their phones by scanning a big QR code at the venue entrance and around social media promos.

After the event I pulled all the data, did a quick analysis (attendance rate, peak registration times, worship team & volunteer numbers, etc.), created a short report with visuals, and sent it to the leadership team. They were really happy — especially because for the first time they had clean, complete, real-time data they could trust and actually use for future planning.

### Main Features

#### Public Registration (registration_app.py)
- Clean, mobile-first form (name, email, phone, optional worship team/volunteer flags)
- Auto-generates unique ticket ID + QR code
- Instant ticket display with download button
- No sidebar, no admin features — super focused
- All data saved to shared SQLite database

#### Admin / Staff Dashboard (app.py)
- **Live stats** on homepage: Total registered, checked-in, check-in rate, pending, worship team & volunteer counts
- Real-time charts (Plotly): check-in progress, registrations over time
- **Multi-mode check-in**:
  - Webcam scan (OpenCV QR detection)
  - Live camera feed
  - Manual ticket ID entry
  - Mobile auto-checkin via URL parameter (?ticket=XXX&action=checkin)
- Manage section: generate bulk tickets, reset data (with backup), system settings
- Export: filtered CSV/Excel/JSON downloads + summary stats
- Google Drive sync (backup & restore registrations)
- Beautiful, dark-mode friendly UI with custom CSS

### How the two apps share data

Both apps import the same classes from these shared files:

- database.py → EventDatabase class (handles SQLite connection, CRUD operations)
- barcode_generator.py` → `BarcodeGenerator` class (QR creation & conversion to bytes)
- utils.py → helper functions (create_sidebar, format_phone, etc.)
- drive_handler.py → Google Drive backup/restore logic

Because they use **the exact same database file** (event_registration.db), every registration done in the public app instantly appears in the admin dashboard stats — no API, no sync delay, just shared SQLite.

### Tech Stack

- Python + Streamlit (frontend & backend in one)
- SQLite (lightweight shared database)
- Plotly (real-time charts & gauges)
- OpenCV (QR scanning)
- qrcode[pil] (QR generation for registration link)
- Google API client libraries (Drive backup)
- pandas (data export & analysis)


### How to Run Locally (for development)

1. Clone the repo
2. pip install -r requirements.txt
3. streamlit run app.py → opens admin dashboard
4. In another terminal: streamlit run registration_app.py → opens registration form

Both should see the same data because they share event_registration.db.

### Lessons Learned / Future Ideas

- SQLite works great for <5k records and single-event use, but for bigger scale I'd move to PostgreSQL or Supabase
- Google Drive backup was a lifesaver — we had an automatic CSV export after every 100 registrations
- People loved the mobile registration — no long queues, no paper forms
- Next version could add SMS/email confirmations, waitlist, or name badge printing

If you're organizing an event and want to avoid losing registration data again, feel free to fork this or reach out — happy to help adapt it.

Thanks for checking it out!

— Ukaba  
Data Analyst & Volunteer, Rooted World Tour 2026




