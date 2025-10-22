from flask import Flask, request
from supabase import create_client, Client
import requests

# ===========================
# 🔧 CONFIG — Hardcoded Values
# ===========================

SUPABASE_URL = "https://utcernnpzhtjrktxrxym.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0Y2Vybm5wemh0anJrdHhyeHltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA5NTM2NDMsImV4cCI6MjA3NjUyOTY0M30.bq1GvZAGCOGG3BrJWPB-F-PFOe7Kk_WLBWOpc-YK2ZI"  # Service Role key from Supabase settings
TWILIO_SID = "AC555bc717a56cd36d9e76a604d7c6c09d"
TWILIO_AUTH_TOKEN = "2163299f04222380be48f486180290b8"
BUCKET_NAME = "Ticket-images"  # Make sure this bucket exists in Supabase

# ===========================
# ⚙️ INIT
# ===========================

app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===========================
# 🧠 ROUTES
# ===========================

@app.route("/", methods=["GET"])
def home():
    return "✅ WhatsApp → Supabase backend running."

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    data = request.form
    num_media = int(data.get("NumMedia", 0))
    sender = data.get("From", "unknown")
    ticket_text = data.get("Body", "").strip() or "No_ticket_number"

    if num_media > 0:
        # Get image from Twilio webhook
        media_url = data.get("MediaUrl0")
        print(f"📩 Received image from {sender}: {media_url}")

        # Download image using Twilio credentials
        img_response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH_TOKEN))
        if img_response.status_code != 200:
            print("⚠️ Error downloading image:", img_response.text)
            return "Error downloading image", 500

        img_bytes = img_response.content

        # Upload to Supabase Storage
        filename = f"{ticket_text.replace(' ', '_')}_{sender[-4:]}.jpg"
        bucket = supabase.storage.from_(BUCKET_NAME)

        upload_res = bucket.upload(filename, img_bytes, {"content-type": "image/jpeg"})
        if hasattr(upload_res, "status_code") and upload_res.status_code != 200:
            print("⚠️ Error uploading:", upload_res.text)
            return "Error uploading to Supabase", 500

        # Get public URL for the uploaded image
        public_url = bucket.get_public_url(filename)

        # Save metadata to Supabase Database
        record = {
            "Ticket_number": ticket_text,
            "sender": sender,
            "image_path": filename,
            "image_url": public_url
        }
        supabase.table("images").insert(record).execute()

        print(f"✅ Uploaded {filename} and saved record for {ticket_text}")
        return "Image saved successfully", 200

    else:
        print("ℹ️ No media found in message")
        return "No media found", 200


# ===========================
# 🚀 RUN SERVER
# ===========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
