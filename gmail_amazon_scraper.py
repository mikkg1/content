#!/usr/bin/env python3
"""
Gmail → Telegram alert for Amazon "Sold, ship now" orders.

Setup:
  1. Create a Google Cloud project, enable Gmail API, download OAuth credentials
     as `credentials.json` (or set GMAIL_CREDENTIALS_FILE in .env).
  2. Create a Telegram bot via @BotFather; get the token and your chat ID.
  3. Copy .env.example → .env and fill in values.
  4. pip install -r requirements.txt
  5. python gmail_amazon_scraper.py
     (First run opens a browser for Gmail OAuth consent.)
"""

import base64
import json
import os
import re
import sys
from email import message_from_bytes
from pathlib import Path

import requests
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
PROCESSED_IDS_FILE = os.getenv("PROCESSED_IDS_FILE", "processed_ids.json")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "50"))

# Shipping service name → box size
ALTAIR_BOX = "10x10"
DEFAULT_BOX = "8x8"


# ── Gmail auth ─────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds = None
    token_path = Path(GMAIL_TOKEN_FILE)
    creds_path = Path(GMAIL_CREDENTIALS_FILE)

    if not creds_path.exists():
        sys.exit(
            f"ERROR: Gmail credentials file not found: {GMAIL_CREDENTIALS_FILE}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ── Processed-ID tracking ──────────────────────────────────────────────────────

def load_processed_ids() -> set:
    path = Path(PROCESSED_IDS_FILE)
    if path.exists():
        return set(json.loads(path.read_text()))
    return set()


def save_processed_ids(ids: set) -> None:
    Path(PROCESSED_IDS_FILE).write_text(json.dumps(sorted(ids)))


# ── Email fetching ─────────────────────────────────────────────────────────────

def fetch_amazon_order_messages(service) -> list[dict]:
    """Return raw message metadata for 'Sold, ship now' emails."""
    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            q='subject:"sold ship now" OR subject:"Sold, ship now"',
            maxResults=MAX_RESULTS,
        )
        .execute()
    )
    return result.get("messages", [])


def get_message_body(service, msg_id: str) -> tuple[str, str]:
    """Return (subject, plain-text body) for a message."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="raw").execute()
    raw = base64.urlsafe_b64decode(msg["raw"])
    email_msg = message_from_bytes(raw)

    subject = email_msg.get("Subject", "")

    body = ""
    if email_msg.is_multipart():
        for part in email_msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                charset = part.get_content_charset() or "utf-8"
                body = part.get_payload(decode=True).decode(charset, errors="replace")
                break
        if not body:
            for part in email_msg.walk():
                if part.get_content_type() == "text/html" and not part.get("Content-Disposition"):
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    body = re.sub(r"<[^>]+>", " ", body)
                    body = re.sub(r"\s{2,}", " ", body)
                    break
    else:
        charset = email_msg.get_content_charset() or "utf-8"
        body = email_msg.get_payload(decode=True).decode(charset, errors="replace")

    return subject, body


# ── Order parsing ──────────────────────────────────────────────────────────────

def _first(pattern: str, text: str, flags: int = re.IGNORECASE) -> str:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else ""


def parse_order(subject: str, body: str) -> dict | None:
    """
    Extract order fields from the email.
    Returns None if the email doesn't look like an Amazon order notification.
    Subject must start with 'Sold' and contain 'ship now' (case-insensitive).
    """
    if not re.match(r"sold[,\s].*ship\s+now", subject, re.IGNORECASE):
        return None

    # Order ID — e.g. 114-1234567-1234567 or 111-XXXXXXX-XXXXXXX
    order_id = _first(r"order[#\s\-:]+([0-9\-]{10,})", body)
    if not order_id:
        order_id = _first(r"\b(\d{3}-\d{7}-\d{7})\b", body)

    # Order date
    order_date = _first(
        r"order\s+date[:\s]+([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        body,
    )

    # Ship by
    ship_by = _first(
        r"ship\s+by[:\s]+([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        body,
    )

    # Item description — try several label variants Amazon uses
    item = (
        _first(r"item[:\s]+(.+)", body)
        or _first(r"product[:\s]+(.+)", body)
        or _first(r"title[:\s]+(.+)", body)
    )
    # Fall back: grab item name from subject after "ship now:"
    if not item:
        m = re.search(r"ship\s+now[:\s]+(.+)", subject, re.IGNORECASE)
        if m:
            item = m.group(1).strip()

    # Quantity
    quantity = (
        _first(r"(?:qty|quantity)[:\s]+(\d+)", body)
        or _first(r"\bquantity\s*ordered[:\s]+(\d+)", body)
        or _first(r"\b(\d+)\s+unit", body)
    )

    # Shipping service
    shipping = (
        _first(r"(?:please\s+ship\s+this\s+order\s+using|shipping\s+service)[:\s]+(.+)", body)
        or _first(r"shipping\s+speed[:\s]+(.+)", body)
        or _first(r"ship\s+method[:\s]+(.+)", body)
        or _first(r"delivery\s+option[:\s]+(.+)", body)
        or _first(r"carrier[:\s]+(.+)", body)
    )

    # SKU
    sku = _first(r"sku[:\s]+(\S+)", body)

    # Box size: 10x10 if SKU, item name, or subject contains "altair"; else 8x8
    altair_match = re.search(r"altair", f"{sku} {item} {subject}", re.IGNORECASE)
    box_size = ALTAIR_BOX if altair_match else DEFAULT_BOX

    return {
        "order_id": order_id or "N/A",
        "order_date": order_date or "N/A",
        "ship_by": ship_by or "N/A",
        "item": item or "N/A",
        "quantity": quantity or "N/A",
        "sku": sku or "N/A",
        "shipping": shipping or "N/A",
        "box_size": box_size,
    }


# ── Telegram alert ─────────────────────────────────────────────────────────────

def send_telegram_alert(order: dict) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping alert.")
        return False

    text = (
        "📦 *New Amazon Order — Ship Now!*\n\n"
        f"*Order ID:*   `{order['order_id']}`\n"
        f"*Order Date:* {order['order_date']}\n"
        f"*Ship By:*    {order['ship_by']}\n"
        f"*Item:*       {order['item']}\n"
        f"*SKU:*        {order['sku']}\n"
        f"*Quantity:*   {order['quantity']}\n"
        f"*Shipping:*   {order['shipping']}\n"
        f"*Box Size:*   {order['box_size']}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        timeout=15,
    )

    if resp.ok:
        print(f"  ✓ Telegram alert sent for order {order['order_id']}")
        return True

    print(f"  ✗ Telegram error {resp.status_code}: {resp.text}")
    return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to Gmail…")
    service = get_gmail_service()

    processed = load_processed_ids()
    print(f"Fetching up to {MAX_RESULTS} 'Sold, ship now' messages…")
    messages = fetch_amazon_order_messages(service)

    if not messages:
        print("No matching messages found.")
        return

    new_count = 0
    for meta in messages:
        msg_id = meta["id"]
        if msg_id in processed:
            continue

        subject, body = get_message_body(service, msg_id)
        print(f"\nProcessing: {subject[:80]}")

        order = parse_order(subject, body)
        if order is None:
            print("  → Skipped (subject doesn't match pattern).")
            processed.add(msg_id)
            continue

        print(
            f"  Order ID={order['order_id']}  "
            f"Ship by={order['ship_by']}  "
            f"Qty={order['quantity']}  "
            f"Box={order['box_size']}"
        )

        if send_telegram_alert(order):
            processed.add(msg_id)
            new_count += 1
        else:
            # Don't mark as processed so we retry next run
            pass

    save_processed_ids(processed)
    print(f"\nDone. {new_count} new alert(s) sent.")


if __name__ == "__main__":
    main()
