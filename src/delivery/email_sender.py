"""
Email Delivery for AI Investing Daily Reports
Sends daily briefings via email.

Setup Options:
1. Gmail (with App Password):
   - Enable 2FA on Google account
   - Generate App Password: Google Account > Security > App Passwords
   - Add to .env:
     EMAIL_PROVIDER=gmail
     EMAIL_ADDRESS=your.email@gmail.com
     EMAIL_PASSWORD=your-app-password

2. Resend (recommended for reliability):
   - Sign up at resend.com
   - Get API key
   - Add to .env:
     EMAIL_PROVIDER=resend
     RESEND_API_KEY=your-api-key
     EMAIL_FROM=reports@yourdomain.com
     EMAIL_TO=you@email.com

3. SendGrid:
   - Sign up at sendgrid.com
   - Get API key
   - Add to .env:
     EMAIL_PROVIDER=sendgrid
     SENDGRID_API_KEY=your-api-key
     EMAIL_FROM=reports@yourdomain.com
     EMAIL_TO=you@email.com
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
import markdown

from dotenv import load_dotenv
load_dotenv()


def markdown_to_html(md_content: str) -> str:
    """Convert markdown report to HTML for email."""
    # Add some basic styling
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            h1 {{ color: #1a1a2e; border-bottom: 2px solid #4a90d9; padding-bottom: 10px; }}
            h2 {{ color: #16213e; margin-top: 30px; }}
            h3 {{ color: #0f3460; }}
            a {{ color: #4a90d9; }}
            code {{
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 0.9em;
            }}
            blockquote {{
                border-left: 4px solid #4a90d9;
                margin: 0;
                padding-left: 20px;
                color: #666;
            }}
            hr {{ border: none; border-top: 1px solid #eee; margin: 20px 0; }}
            .highlight {{ background: #fff3cd; padding: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        {html}
        <hr>
        <p style="color: #888; font-size: 0.9em;">
            Reply to this email with your thoughts - they'll be logged automatically.
        </p>
    </body>
    </html>
    """
    return styled_html


def send_via_gmail(to_email: str, subject: str, html_content: str, text_content: str):
    """Send email via Gmail SMTP."""
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")

    if not email_address or not email_password:
        raise ValueError("EMAIL_ADDRESS and EMAIL_PASSWORD required in .env")

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = email_address
    msg['To'] = to_email

    msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(email_address, email_password)
        server.send_message(msg)

    print(f"✅ Email sent to {to_email}")


def send_via_resend(to_email: str, subject: str, html_content: str):
    """Send email via Resend API."""
    try:
        import resend
    except ImportError:
        raise ImportError("Install resend: pip install resend")

    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("EMAIL_FROM", "reports@resend.dev")

    if not api_key:
        raise ValueError("RESEND_API_KEY required in .env")

    resend.api_key = api_key

    resend.Emails.send({
        "from": from_email,
        "to": to_email,
        "subject": subject,
        "html": html_content
    })

    print(f"✅ Email sent to {to_email} via Resend")


def send_via_sendgrid(to_email: str, subject: str, html_content: str, text_content: str):
    """Send email via SendGrid API."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError:
        raise ImportError("Install sendgrid: pip install sendgrid")

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("EMAIL_FROM")

    if not api_key or not from_email:
        raise ValueError("SENDGRID_API_KEY and EMAIL_FROM required in .env")

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
        plain_text_content=text_content
    )

    sg = SendGridAPIClient(api_key)
    sg.send(message)

    print(f"✅ Email sent to {to_email} via SendGrid")


def send_daily_report_email(to_email: str = None):
    """Generate and send the daily report via email."""
    from src.report_generator import generate_daily_report

    # Get recipient
    to_email = to_email or os.getenv("EMAIL_TO")
    if not to_email:
        raise ValueError("EMAIL_TO required in .env or as argument")

    # Generate report
    report_md = generate_daily_report()

    # Convert to HTML
    html_content = markdown_to_html(report_md)

    # Email details
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"🌅 AI Investing Brief - {today}"

    # Send based on provider
    provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()

    if provider == "gmail":
        send_via_gmail(to_email, subject, html_content, report_md)
    elif provider == "resend":
        send_via_resend(to_email, subject, html_content)
    elif provider == "sendgrid":
        send_via_sendgrid(to_email, subject, html_content, report_md)
    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER: {provider}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        to_email = sys.argv[1]
    else:
        to_email = None

    send_daily_report_email(to_email)
