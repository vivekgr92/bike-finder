import feedparser
import json
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Config
SEEN_FILE = "seen_listings.json"
KEYWORDS = ["R1200GS", "R 1200 GS", "R1200 GS"]
CL_REGIONS = ["sfbay", "sacramento", "monterey", "stockton", "reno"]
MIN_PRICE = 7500
MAX_PRICE = 8500

# Email config from environment
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def search_craigslist(seen):
    new_listings = []
    for region in CL_REGIONS:
        for keyword in KEYWORDS:
            url = (
                f"https://{region}.craigslist.org/search/mca?format=rss"
                f"&query={keyword}&min_price={MIN_PRICE}&max_price={MAX_PRICE}"
            )
            print(f"Checking: {region} for '{keyword}'...")
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title_lower = entry.title.lower()
                # Filter for 2018 model year
                if "2018" in title_lower or "18" in title_lower:
                    if entry.id not in seen:
                        new_listings.append(
                            {
                                "title": entry.title,
                                "link": entry.link,
                                "source": f"CL-{region}",
                                "found_at": datetime.now().isoformat(),
                            }
                        )
                        seen.add(entry.id)
            time.sleep(2)
    return new_listings


def send_email(listings):
    if not all([EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO]):
        print("Email not configured, skipping notification.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"BMW R1200GS Alert: {len(listings)} new listing(s) found!"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Plain text version
    text_lines = [
        f"Found {len(listings)} new BMW R1200GS 2018 listing(s):\n"
    ]
    for listing in listings:
        text_lines.append(f"[{listing['source']}] {listing['title']}")
        text_lines.append(f"  Link: {listing['link']}")
        text_lines.append(f"  Found: {listing['found_at']}\n")
    text_body = "\n".join(text_lines)

    # HTML version
    html_rows = ""
    for listing in listings:
        html_rows += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{listing['source']}</td>
            <td style="padding:8px;border:1px solid #ddd;">
                <a href="{listing['link']}">{listing['title']}</a>
            </td>
            <td style="padding:8px;border:1px solid #ddd;">{listing['found_at']}</td>
        </tr>"""

    html_body = f"""
    <html>
    <body>
        <h2>BMW R1200GS 2018 - New Listings Found!</h2>
        <p>Price range: ${MIN_PRICE:,} - ${MAX_PRICE:,}</p>
        <table style="border-collapse:collapse;width:100%;">
            <tr style="background:#f2f2f2;">
                <th style="padding:8px;border:1px solid #ddd;">Source</th>
                <th style="padding:8px;border:1px solid #ddd;">Listing</th>
                <th style="padding:8px;border:1px solid #ddd;">Found At</th>
            </tr>
            {html_rows}
        </table>
    </body>
    </html>"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"Email sent to {EMAIL_TO}")


def main():
    print(f"=== BMW R1200GS 2018 Search ({datetime.now().isoformat()}) ===")
    print(f"Price range: ${MIN_PRICE:,} - ${MAX_PRICE:,}")

    seen = load_seen()
    new_listings = search_craigslist(seen)
    save_seen(seen)

    if new_listings:
        print(f"\nFound {len(new_listings)} new listing(s):")
        for listing in new_listings:
            print(f"  [{listing['source']}] {listing['title']}")
            print(f"    {listing['link']}")
        send_email(new_listings)
    else:
        print("\nNo new listings found.")


if __name__ == "__main__":
    main()
