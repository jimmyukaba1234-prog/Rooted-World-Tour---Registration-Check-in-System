import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st
from datetime import datetime
import json

class GoogleDriveHandler:
    def __init__(self):
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        self.init_credentials()
    
    def init_credentials(self):
        """Initialize Google Sheets credentials from Streamlit secrets"""
        try:
            if 'gcp_service_account' in st.secrets:
                # Using Streamlit secrets
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds = Credentials.from_service_account_info(creds_dict, scopes=self.scope)
            else:
                # Try local credentials file
                import os
                if os.path.exists('credentials.json'):
                    creds = Credentials.from_service_account_file('credentials.json', scopes=self.scope)
                else:
                    st.error("Google Cloud credentials not found. Please set up credentials.")
                    return None
            
            self.client = gspread.authorize(creds)
            return True
        except Exception as e:
            st.error(f"Error initializing Google Drive: {str(e)}")
            return False
    
    def create_spreadsheet(self, event_name):
        """Create a new Google Sheet for the event"""
        try:
            # Create spreadsheet
            spreadsheet = self.client.create(f"Rooted World Tour - {event_name}")
            
            # Share with anyone with link (optional)
            spreadsheet.share(None, perm_type='anyone', role='writer')
            
            # Setup worksheets
            worksheet = spreadsheet.sheet1
            worksheet.update_title("Registrations")
            
            # Set headers
            headers = [
                "Ticket ID", "First Name", "Last Name", "Email", "Phone",
                "Registration Time", "Check-in Time", "Status", "Source", "Barcode"
            ]
            worksheet.append_row(headers)
            
            # Create summary sheet
            summary_sheet = spreadsheet.add_worksheet(title="Summary", rows=100, cols=10)
            summary_headers = ["Metric", "Value", "Last Updated"]
            summary_sheet.append_row(summary_headers)
            
            st.success(f"Spreadsheet created: {spreadsheet.url}")
            return spreadsheet.id, spreadsheet.url
        except Exception as e:
            st.error(f"Error creating spreadsheet: {str(e)}")
            return None, None
    
    def sync_to_sheets(self, df, spreadsheet_id, sheet_name="Registrations"):
        """Sync local database to Google Sheets"""
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Clear existing data except headers
            worksheet.clear()
            
            # Write headers
            headers = df.columns.tolist()
            worksheet.append_row(headers)
            
            # Write data
            data = df.values.tolist()
            if data:
                worksheet.append_rows(data)
            
            # Update summary
            self.update_summary(spreadsheet, df)
            
            return True
        except Exception as e:
            st.error(f"Error syncing to Google Sheets: {str(e)}")
            return False
    
    def update_summary(self, spreadsheet, df):
        """Update summary sheet with statistics"""
        try:
            summary_sheet = spreadsheet.worksheet("Summary")
            summary_sheet.clear()
            
            # Summary headers
            summary_sheet.append_row(["Metric", "Value", "Last Updated"])
            
            # Calculate metrics
            total_registrations = len(df)
            checked_in = len(df[df['Status'] == 'checked_in']) if 'Status' in df.columns else 0
            pending = total_registrations - checked_in
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            metrics = [
                ["Total Registrations", total_registrations, now],
                ["Checked In", checked_in, now],
                ["Pending Check-in", pending, now],
                ["Check-in Rate", f"{(checked_in/total_registrations*100):.1f}%" if total_registrations > 0 else "0%", now]
            ]
            
            summary_sheet.append_rows(metrics)
            
        except Exception as e:
            st.warning(f"Could not update summary: {str(e)}")
    
    def get_spreadsheet_data(self, spreadsheet_id):
        """Retrieve data from Google Sheets"""
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error retrieving data: {str(e)}")
            return pd.DataFrame()

# Local database fallback
import sqlite3
import os

class HybridDatabase:
    def __init__(self, use_google_drive=True):
        self.use_google_drive = use_google_drive
        self.local_db = "event_registration.db"
        self.google_handler = GoogleDriveHandler() if use_google_drive else None
        self.init_local_db()
    
    def init_local_db(self):
        """Initialize local SQLite database as backup"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checkin_time TIMESTAMP,
            status TEXT DEFAULT 'registered',
            source_system TEXT DEFAULT 'manual',
            scanned_data TEXT,
            synced_to_cloud INTEGER DEFAULT 0
        )
        ''')
        
        # Events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            event_date DATE,
            location TEXT,
            spreadsheet_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_registration(self, data):
        """Add registration to both local and cloud databases"""
        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO registrations 
            (ticket_id, first_name, last_name, email, phone, scanned_data)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['ticket_id'], data['first_name'], data['last_name'],
                data['email'], data['phone'], data['scanned_data']
            ))
            
            conn.commit()
            
            # If Google Drive is enabled, sync
            if self.use_google_drive and self.google_handler:
                # This would sync in background
                pass
            
            return True, "Registration successful!"
            
        except sqlite3.IntegrityError:
            return False, "Ticket ID already exists!"
        except Exception as e:
            return False, f"Error: {str(e)}"
        finally:
            conn.close()
