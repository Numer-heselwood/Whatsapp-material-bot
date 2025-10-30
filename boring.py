from flask import Flask, request
from supabase import create_client, Client
import requests

# --- CONFIG (hardcoded for simplicity) ---
SUPABASE_URL = "https://utcernnpzhtjrktxrxym.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0Y2Vybm5wemh0anJrdHhyeHltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA5NTM2NDMsImV4cCI6MjA3NjUyOTY0M30.bq1GvZAGCOGG3BrJWPB-F-PFOe7Kk_WLBWOpc-YK2ZI"
TWILIO_SID = "AC555bc717a56cd36d9e76a604d7c6c09d"
TWILIO_AUTH_TOKEN = "2163299f04222380be48f486180290b8"
BUCKET_NAME = "Ticket-images"

# --- INIT ---
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- ROUTES ---
@app.route("/", methods=["GET"])
def home():
    return "WhatsApp → Supabase backend is running."


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    data = request.form
    num_media = int(data.get("NumMedia", 0))
    sender = data.get("From", "unknown")
    ticket_text = data.get("Body", "").strip() or "No_ticket_number"

    if num_media == 0:
        print("No media in message.")
        return "No media found", 200

    # Download the image from Twilio
    media_url = data.get("MediaUrl0")
    print(f"Received image from {sender}: {media_url}")

    response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH_TOKEN))
    if response.status_code != 200:
        print("Failed to download image:", response.text)
        return "Error downloading image", 500

    image_data = response.content
    filename = f"{ticket_text.replace(' ', '_')}_{sender[-4:]}.jpg"

    # Upload to Supabase storage
    bucket = supabase.storage().from_(BUCKET_NAME)
    upload_res = bucket.upload(filename, image_data)

    if not upload_res:
        print("Upload failed.")
        return "Error uploading to Supabase", 500

    public_url = bucket.get_public_url(filename)

    # Save record in database
    supabase.table("images").insert({
        "Ticket_number": ticket_text,
        "sender": sender,
        "image_path": filename,
        "image_url": public_url
    }).execute()

    print(f"Uploaded {filename} for ticket {ticket_text}")
    return "Image saved successfully", 200


# --- RUN SERVER ---
if __name__ == "__main__":
    print("✅ WhatsApp → Supabase backend running on port 8050")
    app.run(host="127.0.0.1", port=8050, debug=True)
