"""
Notification Pipeline — SMS (Twilio), Email (SMTP), Webhook.
All non-blocking via background threads.
"""

import threading
import time
import smtplib
import json
from email.mime.text import MIMEText
from typing import List

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM,
    ALERT_PHONE_NUMBERS, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS,
    ALERT_EMAILS, WEBHOOK_URL, ALERT_DANGER, ALERT_CRITICAL
)


class NotificationPipeline:
    def __init__(self):
        self._sent_log: List[dict] = []

    def send_all(self, event):
        """Called by AlertEngine callback. Dispatches all channels async."""
        if event.level not in (ALERT_DANGER, ALERT_CRITICAL):
            return
        threading.Thread(target=self._send_sms, args=(event,), daemon=True).start()
        threading.Thread(target=self._send_email, args=(event,), daemon=True).start()
        threading.Thread(target=self._send_webhook, args=(event,), daemon=True).start()

    def _send_sms(self, event):
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print(f"[Notify] SMS (simulated): [{event.level}] {event.message}")
            self._log("sms", event.level, "simulated")
            return
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            for number in ALERT_PHONE_NUMBERS:
                number = number.strip()
                if number:
                    client.messages.create(
                        body=f"[CROWD ALERT] {event.level}: {event.message}",
                        from_=TWILIO_FROM, to=number
                    )
            self._log("sms", event.level, "sent")
        except Exception as e:
            print(f"[Notify] SMS error: {e}")
            self._log("sms", event.level, f"error:{e}")

    def _send_email(self, event):
        if not SMTP_USER or not SMTP_PASS:
            print(f"[Notify] Email (simulated): [{event.level}] {event.message}")
            self._log("email", event.level, "simulated")
            return
        try:
            msg = MIMEText(
                f"Alert Level: {event.level}\n\n{event.message}\n\nMetrics:\n"
                + "\n".join(f"  {k}: {v}" for k, v in event.metrics.items())
            )
            msg["Subject"] = f"[CROWD SAFETY] {event.level} Alert"
            msg["From"] = SMTP_USER
            msg["To"] = ", ".join(ALERT_EMAILS)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_USER, ALERT_EMAILS, msg.as_string())
            self._log("email", event.level, "sent")
        except Exception as e:
            print(f"[Notify] Email error: {e}")
            self._log("email", event.level, f"error:{e}")

    def _send_webhook(self, event):
        if not WEBHOOK_URL:
            self._log("webhook", event.level, "not_configured")
            return
        try:
            import requests
            requests.post(WEBHOOK_URL, json={
                "level": event.level,
                "message": event.message,
                "timestamp": event.timestamp,
                "metrics": event.metrics
            }, timeout=5)
            self._log("webhook", event.level, "sent")
        except Exception as e:
            print(f"[Notify] Webhook error: {e}")

    def _log(self, channel: str, level: str, status: str):
        self._sent_log.append({
            "channel": channel, "level": level, "status": status, "time": time.time()
        })
