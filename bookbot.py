import requests
from bs4 import BeautifulSoup
import time
import random
import os
from twilio.rest import Client

# ================= CONFIG =================
URL = "https://checkvisaslots.com/latest-us-visa-availability/f-1-regular/"

# Twilio
ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
YOUR_NUMBER = os.getenv("YOUR_NUMBER")

# ==========================================

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Prevent spam alerts
last_alert_time = 0
ALERT_COOLDOWN = 600  # 10 minutes


# ---------- SMS ----------
def send_sms(msg):
    client.messages.create(
        body=msg,
        from_=TWILIO_NUMBER,
        to=YOUR_NUMBER
    )
    print("📱 SMS sent")


# ---------- CALL ----------
def make_call():
    client.calls.create(
        twiml='<Response><Say>Alert! Mumbai visa slot is available. Check immediately.</Say></Response>',
        to=YOUR_NUMBER,
        from_=TWILIO_NUMBER
    )
    print("📞 Calling...")


# ---------- EXTRACT MUMBAI DATA ----------
def extract_mumbai_data():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.find_all("tr")

    for row in rows:
        cols = [c.text.strip() for c in row.find_all("td")]

        if len(cols) > 0 and "mumbai" in cols[0].lower():
            try:
                total_dates = int(cols[4]) if cols[4].isdigit() else 0
            except:
                total_dates = 0

            return {
                "location": cols[0],
                "earliest_date": cols[2],
                "total_dates": total_dates,
                "last_seen": cols[5]
            }

    return None


# ---------- MAIN LOOP ----------
previous_data = None

while True:
    try:
        print(f"\n🔍 Checking at {time.ctime()}")

        current_data = extract_mumbai_data()

        if current_data:
            print("📊 Current Data:", current_data)

            if previous_data:
                trigger = None

                # 🔥 1. Earliest date changed
                if current_data["earliest_date"] != previous_data["earliest_date"]:
                    trigger = f"📅 New slot date: {current_data['earliest_date']}"

                # 🔥 2. More slots added
                elif current_data["total_dates"] > previous_data["total_dates"]:
                    trigger = f"📈 Slots increased: {current_data['total_dates']}"

                # 🔥 3. Fresh update detected
                elif current_data["last_seen"] != previous_data["last_seen"]:
                    trigger = "⚡ Fresh update detected!"

                # ---------- ALERT ----------
                if trigger:
                    if time.time() - last_alert_time > ALERT_COOLDOWN:
                        message = f"🚨 {trigger}\nMumbai VAC slots updated!\nCheck immediately!"

                        print("🚨 ALERT:", message)

                        send_sms(message)
                        make_call()

                        last_alert_time = time.time()
                    else:
                        print("⏳ Cooldown active, skipping alert")

            previous_data = current_data

        else:
            print("❌ Mumbai data not found")

        # Random delay to stay safe
        sleep_time = random.randint(120, 240)
        print(f"⏳ Sleeping {sleep_time} seconds...")
        time.sleep(sleep_time)

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)