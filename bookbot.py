import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from twilio.rest import Client
import os

# ================= CONFIG =================
URL = "https://checkvisaslots.com/latest-us-visa-availability/f-1-regular/"

ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
YOUR_NUMBER = os.getenv("YOUR_NUMBER")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Cooldown
last_alert_time = 0
ALERT_COOLDOWN = 600  # 10 min

# ---------- ALERTS ----------
def send_sms(msg):
    client.messages.create(
        body=msg,
        from_=TWILIO_NUMBER,
        to=YOUR_NUMBER
    )
    print("📱 SMS sent")

def make_call():
    client.calls.create(
        twiml='<Response><Say>Mumbai visa slot update detected. Check immediately.</Say></Response>',
        to=YOUR_NUMBER,
        from_=TWILIO_NUMBER
    )
    print("📞 Calling...")

# ---------- SETUP SELENIUM ----------
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ---------- EXTRACT MUMBAI VAC ----------
def extract_mumbai_data():
    driver.get(URL)
    time.sleep(5)  # wait for JS to load

    rows = driver.find_elements(By.TAG_NAME, "tr")

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        cols = [c.text.strip() for c in cols]

        if len(cols) > 0:
            location = cols[0].lower()

            # 🎯 STRICT MATCH
            if location == "mumbai vac":
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
            print("📊 Current:", current_data)

            if previous_data:
                trigger = None

                # 🔥 Detect changes
                if current_data["earliest_date"] != previous_data["earliest_date"]:
                    trigger = f"📅 New date: {current_data['earliest_date']}"

                elif current_data["total_dates"] > previous_data["total_dates"]:
                    trigger = f"📈 Slots increased: {current_data['total_dates']}"

                elif current_data["last_seen"] != previous_data["last_seen"]:
                    trigger = "⚡ Fresh update detected!"

                if trigger:
                    if time.time() - last_alert_time > ALERT_COOLDOWN:
                        msg = f"🚨 {trigger}\nMumbai VAC updated! Check now!"
                        print(msg)

                        send_sms(msg)
                        make_call()

                        last_alert_time = time.time()
                    else:
                        print("⏳ Cooldown active")

            previous_data = current_data

        else:
            print("❌ Mumbai VAC not found")

        sleep_time = random.randint(120, 240)
        print(f"⏳ Sleeping {sleep_time} sec")
        time.sleep(sleep_time)

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)