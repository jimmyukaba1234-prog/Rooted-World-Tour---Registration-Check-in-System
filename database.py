import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st

class EventDatabase:
    def __init__(self, db_path="event_registration.db"):
        self.db_path = db_path
        from barcode_generator import BarcodeGenerator
        self.barcode_gen = BarcodeGenerator()
        self.init_db()
        self.update_database_schema()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Enhanced registrations table
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
            emergency_contact TEXT,
            medical_notes TEXT,
            worship_team INTEGER DEFAULT 0,
            volunteer INTEGER DEFAULT 0,
            synced_to_cloud INTEGER DEFAULT 0
        )
        ''')
        
        # Events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            event_date DATE,
            start_time TIME,
            end_time TIME,
            location TEXT,
            capacity INTEGER,
            spreadsheet_id TEXT,
            registration_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Check-in stations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkin_stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_name TEXT NOT NULL,
            station_code TEXT UNIQUE,
            location TEXT,
            ip_address TEXT,
            last_active TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_database_schema(self):
        """Update database schema to add missing columns"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if scanned_data column exists
            cursor.execute("PRAGMA table_info(registrations)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns if they don't exist
            columns_to_add = [
                ('scanned_data', 'TEXT DEFAULT ""'),
                ('emergency_contact', 'TEXT DEFAULT ""'),
                ('medical_notes', 'TEXT DEFAULT ""'),
                ('worship_team', 'INTEGER DEFAULT 0'),
                ('volunteer', 'INTEGER DEFAULT 0'),
                ('synced_to_cloud', 'INTEGER DEFAULT 0')
            ]
            
            for column_name, column_type in columns_to_add:
                if column_name not in columns:
                    cursor.execute(f"ALTER TABLE registrations ADD COLUMN {column_name} {column_type}")
                    print(f"Added {column_name} column")
            
            conn.commit()
            print("Database schema updated successfully")
            
        except Exception as e:
            print(f"Error updating schema: {str(e)}")
        finally:
            conn.close()
    
    def create_event(self, event_name, event_date, location, capacity=1000):
        """Create a new event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Generate registration URL with unique ID
        import uuid
        event_code = str(uuid.uuid4())[:8]
        registration_url = f"https://rooted-world-tour.streamlit.app/?event={event_code}"
        
        cursor.execute('''
        INSERT INTO events (event_name, event_date, location, capacity, registration_url)
        VALUES (?, ?, ?, ?, ?)
        ''', (event_name, event_date, location, capacity, registration_url))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return event_id, registration_url
    
    def add_registration(self, data):
        """Add a new registration with all required fields"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Generate ticket ID if not provided
        if 'ticket_id' not in data or not data['ticket_id']:
            data['ticket_id'] = self.barcode_gen.generate_ticket_id()
        
        # Generate CHECK-IN QR code
        qr_img = self.barcode_gen.create_checkin_qr(data['ticket_id'])
        
        # Ensure all required fields have defaults
        registration_data = {
            'ticket_id': data['ticket_id'],
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'emergency_contact': data.get('emergency_contact', ''),
            'medical_notes': data.get('medical_notes', ''),
            'worship_team': data.get('worship_team', 0),
            'volunteer': data.get('volunteer', 0),
            'scanned_data': data.get('scanned_data', 'manual_registration')
        }
        
        try:
            cursor.execute('''
            INSERT INTO registrations 
            (ticket_id, first_name, last_name, email, phone, 
             emergency_contact, medical_notes, worship_team, volunteer, scanned_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                registration_data['ticket_id'],
                registration_data['first_name'],
                registration_data['last_name'],
                registration_data['email'],
                registration_data['phone'],
                registration_data['emergency_contact'],
                registration_data['medical_notes'],
                registration_data['worship_team'],
                registration_data['volunteer'],
                registration_data['scanned_data']
            ))
            
            conn.commit()
            conn.close()
            
            return True, "Registration successful!", data['ticket_id'], qr_img
            
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Ticket ID already exists!", None, None
        except Exception as e:
            conn.close()
            return False, f"Error: {str(e)}", None, None
    
    def quick_checkin(self, ticket_id):
        """Quick check-in using ticket ID or barcode scan"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # First try exact ticket ID match
        cursor.execute('''
        UPDATE registrations 
        SET checkin_time = ?, status = 'checked_in'
        WHERE ticket_id = ? AND status = 'registered'
        ''', (datetime.now(), ticket_id))
        
        if cursor.rowcount == 0:
            # Try partial match
            cursor.execute('''
            UPDATE registrations 
            SET checkin_time = ?, status = 'checked_in'
            WHERE ticket_id LIKE ? AND status = 'registered'
            ''', (datetime.now(), f"%{ticket_id}%"))
        
        conn.commit()
        updated = cursor.rowcount > 0
        
        if updated:
            cursor.execute('SELECT first_name, last_name FROM registrations WHERE ticket_id LIKE ?', (f"%{ticket_id}%",))
            attendee = cursor.fetchone()
            conn.close()
            return True, attendee
        else:
            # Check if already checked in
            cursor.execute('SELECT first_name, last_name, status FROM registrations WHERE ticket_id LIKE ?', (f"%{ticket_id}%",))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[2] == 'checked_in':
                return False, (result[0], result[1])  # Return attendee info
            return False, None
    
    def get_dashboard_stats(self, event_date=None):
        """Get comprehensive dashboard statistics"""
        conn = self.get_connection()
        
        stats = {}
        
        # Base query with COALESCE to handle NULL values
        query = "SELECT "
        query += "COUNT(*) as total, "
        query += "COALESCE(SUM(CASE WHEN status = 'checked_in' THEN 1 ELSE 0 END), 0) as checked_in, "
        query += "COALESCE(SUM(CASE WHEN worship_team = 1 THEN 1 ELSE 0 END), 0) as worship_team, "
        query += "COALESCE(SUM(CASE WHEN volunteer = 1 THEN 1 ELSE 0 END), 0) as volunteers, "
        query += "COUNT(DISTINCT date(registration_time)) as active_days "
        query += "FROM registrations"
        
        params = ()
        
        if event_date:
            query += " WHERE date(registration_time) = ?"
            params = (event_date,)
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        # Initialize all stats with 0 to avoid None values
        stats['total'] = result[0] or 0 if result else 0
        stats['checked_in'] = result[1] or 0 if result and result[1] is not None else 0
        stats['worship_team'] = result[2] or 0 if result and result[2] is not None else 0
        stats['volunteers'] = result[3] or 0 if result and result[3] is not None else 0
        stats['active_days'] = result[4] or 0 if result and result[4] is not None else 0
        
        # Calculate derived stats safely
        stats['pending'] = stats['total'] - stats['checked_in']
        
        if stats['total'] > 0:
            stats['checkin_rate'] = f"{(stats['checked_in'] / stats['total'] * 100):.1f}%"
        else:
            stats['checkin_rate'] = "0%"
        
        # Hourly check-ins for today
        cursor.execute('''
        SELECT strftime('%H', checkin_time) as hour, COUNT(*) as count
        FROM registrations 
        WHERE date(checkin_time) = date('now') 
        AND status = 'checked_in'
        AND checkin_time IS NOT NULL
        GROUP BY hour
        ORDER BY hour
        ''')
        
        hourly_data = cursor.fetchall()
        stats['hourly_checkins'] = {str(hour): count for hour, count in hourly_data}
        
        conn.close()
        return stats
    
    def search_registrations(self, search_term):
        """Search registrations by name, email, or ticket ID"""
        conn = self.get_connection()
        
        query = '''
        SELECT ticket_id, first_name, last_name, email, phone, status, 
               datetime(registration_time) as reg_time
        FROM registrations
        WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR ticket_id LIKE ?
        ORDER BY registration_time DESC
        LIMIT 50
        '''
        
        search_pattern = f"%{search_term}%"
        df = pd.read_sql_query(query, conn, params=(search_pattern, search_pattern, 
                                                   search_pattern, search_pattern))
        conn.close()
        
        if 'phone' in df.columns:
            df['phone'] = df['phone'].astype(str)
            df['phone'] = df['phone'].apply(lambda x: str(x).replace(',', '') if pd.notna(x) else '')

        return df
    
    def get_recent_registrations(self, limit=20):
        """Get recent registrations"""
        conn = self.get_connection()
        
        query = f'''
        SELECT ticket_id, first_name, last_name, email, status, 
               datetime(registration_time) as reg_time
        FROM registrations
        ORDER BY registration_time DESC
        LIMIT {limit}
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if 'phone' in df.columns:
            df['phone'] = df['phone'].astype(str)
            df['phone'] = df['phone'].apply(lambda x: str(x).replace(',', '') if pd.notna(x) else '')
        
        return df
    
    def backup_database(self, backup_dir="backups"):
        """Create a backup of the database"""
        import os
        import shutil
        from datetime import datetime
        
        try:
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"event_registration_backup_{timestamp}.db")
            
            # Copy the database file
            shutil.copy2(self.db_path, backup_path)
            
            # Also export to CSV
            csv_path = os.path.join(backup_dir, f"registrations_backup_{timestamp}.csv")
            self.export_to_csv(csv_path)
            
            return backup_path
            
        except Exception as e:
            raise Exception(f"Backup failed: {str(e)}")

    def export_to_csv(self, filepath):
        """Export all registrations to CSV"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM registrations", conn)
        conn.close()
        
        if 'phone' in df.columns:
            df['phone'] = df['phone'].astype(str)
            df['phone'] = df['phone'].apply(lambda x: str(x).replace(',', '') if pd.notna(x) else '')
        
        if not df.empty:
            df.to_csv(filepath, index=False)
            return True
        return False

    def import_from_csv(self, filepath):
        """Import registrations from CSV"""
        try:
            df = pd.read_csv(filepath)
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                try:
                    cursor.execute('''
                    INSERT OR REPLACE INTO registrations 
                    (ticket_id, first_name, last_name, email, phone, status, 
                    registration_time, checkin_time, worship_team, volunteer)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('ticket_id'),
                        row.get('first_name'),
                        row.get('last_name'),
                        row.get('email'),
                        row.get('phone'),
                        row.get('status', 'registered'),
                        row.get('registration_time'),
                        row.get('checkin_time'),
                        row.get('worship_team', 0),
                        row.get('volunteer', 0)
                    ))
                except Exception as e:
                    print(f"Error importing row: {e}")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Import failed: {e}")
            return False
