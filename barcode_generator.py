import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import streamlit as st
import uuid

class EventQRGenerator:
    def __init__(self):
        self.base_url = st.secrets.get("APP_URL", "https://event-registration-backup-system-2yuhtnkp6z9xhwq3wbqcoo.streamlit.app")
    
    def generate_ticket_id(self, prefix="RWT"):
        """Generate unique ticket ID with prefix"""
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"{prefix}-{unique_id}"
    
    def create_registration_qr(self, ticket_id=None, registration_url=None):
        """Generate QR code for registration - works with or without ticket_id"""
        if ticket_id is None:
            # Generate a new ticket ID for the registration QR
            ticket_id = self.generate_ticket_id()
        
        if registration_url is None:
            # For homepage QR: link to registration page
            # For check-in QR: link with ticket ID and action
            if "checkin" in st.session_state.get('current_page', '').lower():
                registration_url = f"{self.base_url}/?ticket={ticket_id}&action=checkin"
            else:
                registration_url = f"{self.base_url}/?page=Register"
        
        # Create QR code
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        qr.add_data(registration_url)
        qr.make(fit=True)
        
        # Get QR code image as RGB
        qr_img = qr.make_image(fill_color="#4CAF50", back_color="white").convert('RGB')
        
        # Get QR code dimensions
        qr_width, qr_height = qr_img.size
        
        # Create final image with exact dimensions
        final_width = max(400, qr_width + 100)  # Ensure minimum width
        final_height = qr_height + 180  # Add space for text
        
        final_img = Image.new('RGB', (final_width, final_height), color='white')
        
        # Calculate position to center the QR code
        qr_x = (final_width - qr_width) // 2
        qr_y = 30
        
        # Paste QR code at calculated position
        final_img.paste(qr_img, (qr_x, qr_y))
        
        # Add text
        draw = ImageDraw.Draw(final_img)
        
        # Try to load font
        try:
            font_large = ImageFont.truetype("Arial.ttf", 24)
            font_medium = ImageFont.truetype("Arial.ttf", 18)
            font_small = ImageFont.truetype("Arial.ttf", 14)
        except:
            # Use default font if Arial not available
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Calculate text positions
        text_y = qr_y + qr_height + 20
        
        # Add ticket ID (only if provided)
        if ticket_id:
            draw.text((final_width // 2, text_y), 
                     f"Ticket: {ticket_id}", 
                     fill="black", 
                     font=font_medium, 
                     anchor="mm")
            text_y += 30
        
        # Add title based on context
        if "checkin" in registration_url.lower():
            draw.text((final_width // 2, text_y), 
                     "Check-in QR Code", 
                     fill="#4CAF50", 
                     font=font_large, 
                     anchor="mm")
        else:
            draw.text((final_width // 2, text_y), 
                     "Mobile Registration", 
                     fill="#4CAF50", 
                     font=font_large, 
                     anchor="mm")
        
        # Add instructions
        if "checkin" in registration_url.lower():
            instructions = [
                "Scan this QR code at the event",
                "for instant check-in"
            ]
        else:
            instructions = [
                "1. Scan with phone camera",
                "2. Complete registration form",
                "3. Receive your digital ticket"
            ]
        
        for i, line in enumerate(instructions):
            draw.text((final_width // 2, text_y + 35 + (i * 25)), 
                     line, 
                     fill="#666666", 
                     font=font_small, 
                     anchor="mm")
        
        # Add branding
        draw.text((final_width // 2, final_height - 30), 
                 "Rooted World Tour", 
                 fill="#1a5319", 
                 font=font_medium, 
                 anchor="mm")
        
        return final_img
    
    def create_checkin_qr(self, ticket_id):
        """Create QR code for check-in (after registration)"""
        # URL that mobile cameras will recognize
        checkin_url = f"{self.base_url}/?ticket={ticket_id}&action=checkin"
        
        # Make the QR code robust
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=12,
            border=4,
        )
        qr.add_data(checkin_url)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="#1a5319", back_color="white")
        qr_img = qr_img.convert('RGB')
        
        # Get QR code dimensions
        qr_width, qr_height = qr_img.size
        
        # Create ticket design
        final_width = max(400, qr_width + 100)  # Ensure minimum width
        final_height = qr_height + 180  # Add space for text
        
        final_img = Image.new('RGB', (final_width, final_height), color='white')
        draw = ImageDraw.Draw(final_img)
        
        # Add header with gradient
        for i in range(60):
            y = i
            draw.rectangle([0, y, final_width, y+1], fill=(26, 83, 25))
        
        # Try to load fonts
        try:
            font_title = ImageFont.truetype("arial.ttf", 28)
            font_subtitle = ImageFont.truetype("arial.ttf", 18)
            font_medium = ImageFont.truetype("arial.ttf", 20)
            font_small = ImageFont.truetype("arial.ttf", 14)
            font_tiny = ImageFont.truetype("arial.ttf", 12)
        except:
            # Fallback to default fonts
            font_title = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()
        
        # Event title
        draw.text((final_width // 2, 30),
                 "🌿 ROOTED WORLD TOUR",
                 fill="white",
                 font=font_title,
                 anchor="mm")
        
        draw.text((final_width // 2, 65),
                 "Worship Night Encounter",
                 fill="#FFD700",
                 font=font_subtitle,
                 anchor="mm")
        
        # Add QR code
        qr_width, qr_height = qr_img.size
        qr_x = (final_width - qr_width) // 2
        qr_y = 120
        
        final_img.paste(qr_img, (qr_x, qr_y))
        
        # Ticket info box
        info_y = qr_y + qr_height + 30
        draw.rectangle([50, info_y, final_width-50, info_y + 120], 
                      fill="#f8f9fa", 
                      outline="#4CAF50", 
                      width=2)
        
        # Ticket ID
        draw.text((final_width // 2, info_y + 25),
                 f"🎫 TICKET ID: {ticket_id}",
                 fill="#1a5319",
                 font=font_medium,
                 anchor="mm")
        
        # Check-in instructions
        instructions = [
            "📱 CHECK-IN INSTRUCTIONS:",
            "1. Present this QR code at event entry",
            "2. Staff will scan with phone or webcam",
            "3. Instant verification and entry",
            "4. Keep this ticket safe!"
        ]
        
        for i, instruction in enumerate(instructions):
            y_pos = info_y + 50 + (i * 25)
            color = "#1a5319" if i == 0 else "#333333"
            font_size = font_medium if i == 0 else font_small
            draw.text((final_width // 2, y_pos),
                     instruction,
                     fill=color,
                     font=font_size,
                     anchor="mm")
        
        # Mobile instructions
        draw.text((final_width // 2, final_height - 60),
                 "📱 MOBILE CHECK-IN: Open phone camera → Point at QR → Tap link",
                 fill="#4CAF50",
                 font=font_small,
                 anchor="mm")
        
        # Footer
        draw.text((final_width // 2, final_height - 30),
                 "Digital Ticket • Valid for one entry",
                 fill="#666666",
                 font=font_tiny,
                 anchor="mm")
        
        return final_img
    
    def img_to_bytes(self, img):
        """Convert PIL image to bytes for download"""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    
    def generate_bulk_qr_codes(self, count, prefix="RWT"):
        """Generate multiple QR codes for print"""
        tickets = []
        for i in range(count):
            ticket_id = self.generate_ticket_id(prefix)
            qr_img = self.create_checkin_qr(ticket_id)
            tickets.append({
                'ticket_id': ticket_id,
                'qr_image': qr_img,
                'qr_data': f"{self.base_url}/?ticket={ticket_id}&action=checkin"
            })               
        return tickets

# Use this class as BarcodeGenerator
BarcodeGenerator = EventQRGenerator
