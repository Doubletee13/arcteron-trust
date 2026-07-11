from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime
from app.config import settings

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"


def get_template(filename: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(filename)
    return template


def send_email(to: str, subject: str, html_content: str):
    # Use SMTP if MAIL_SERVER is not Resend or SendGrid (i.e. local MailHog)
    if settings.MAIL_SERVER not in ["smtp.resend.com", "smtp.sendgrid.net"]:
        # Local SMTP via MailHog
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.APP_NAME} <{settings.MAIL_FROM}>"
        msg['To'] = to

        part = MIMEText(html_content, 'html')
        msg.attach(part)

        try:
            with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                server.sendmail(settings.MAIL_FROM, to, msg.as_string())
            print(f"EMAIL (LOCAL SMTP) TO: {to} | SUBJECT: {subject}")
        except ConnectionRefusedError:
            print(f"MOCKED EMAIL TO: {to} | SUBJECT: {subject} (Local SMTP down, bypassing)")
            
        return {"status_code": 250}
    else:
        # Production: HTTP API (SendGrid or Resend) via Python standard urllib
        import urllib.request
        import urllib.error
        import json

        is_sendgrid = settings.MAIL_SERVER == "smtp.sendgrid.net"

        if is_sendgrid:
            url = "https://api.sendgrid.com/v3/mail/send"
            payload = {
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": settings.MAIL_FROM, "name": settings.APP_NAME},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}]
            }
            provider = "SENDGRID"
        else:
            # Resend
            url = "https://api.resend.com/emails"
            payload = {
                "from": f"{settings.APP_NAME} <{settings.MAIL_FROM}>",
                "to": [to],
                "subject": subject,
                "html": html_content
            }
            provider = "RESEND"

        headers = {
            "Authorization": f"Bearer {settings.MAIL_PASSWORD}",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8")
                print(f"EMAIL ({provider}) TO: {to} | STATUS: {status_code}")
                class MockResponse:
                    def __init__(self, sc, b):
                        self.status_code = sc
                        self.body = b
                return MockResponse(status_code, body)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(f"{provider} ERROR {e.code}: {e.reason} | BODY: {error_body}")
            raise e
        except Exception as e:
            print(f"FAILED TO SEND EMAIL VIA {provider}: {e}")
            raise e


def send_login_alert(
    to: str,
    first_name: str,
    email: str,
    account_last_four: str
):
    template = get_template("login_alert.html")
    html = template.render(
        first_name=first_name,
        email=email,
        account_last_four=account_last_four,
        login_time=datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC"),
        frontend_url=settings.FRONTEND_URL,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — New Login Detected", html)


def send_password_reset_email(to: str, first_name: str, token: str):
    reset_url = f"{settings.FRONTEND_URL}/pages/reset-password.html?token={token}"
    template = get_template("password_reset.html")
    html = template.render(
        first_name=first_name,
        reset_url=reset_url,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — Password Reset Request", html)


def send_pin_reset_email(to: str, first_name: str, token: str):
    reset_url = f"{settings.FRONTEND_URL}/pages/reset-pin.html?token={token}"
    template = get_template("pin_reset.html")
    html = template.render(
        first_name=first_name,
        reset_url=reset_url,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — PIN Reset Request", html)


def send_verification_email(to: str, first_name: str, otp_code: str):
    template = get_template("email_verification_otp.html")
    html = template.render(
        first_name=first_name,
        otp_code=otp_code,
        frontend_url=settings.FRONTEND_URL,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — Verify Your Email Address", html)


def send_welcome_email(
    to: str,
    first_name: str,
    full_name: str,
    account_number: str,
    account_type: str,
    country: str
):
    template = get_template("welcome.html")
    html = template.render(
        first_name=first_name,
        full_name=full_name,
        account_number=account_number,
        account_type=account_type.capitalize(),
        country=country,
        created_date=datetime.utcnow().strftime("%B %d, %Y"),
        frontend_url=settings.FRONTEND_URL,
        year=datetime.utcnow().year
    )
    send_email(to, f"Welcome to {settings.APP_NAME} — Your Account Is Ready", html)


def send_transfer_sent_email(
    to: str,
    first_name: str,
    amount: str,
    reference: str,
    recipient_name: str,
    recipient_account_last_four: str,
    transaction_date: str,
    description: str,
    new_balance: str
):
    template = get_template("transfer_sent.html")
    html = template.render(
        first_name=first_name,
        amount=amount,
        reference=reference,
        recipient_name=recipient_name,
        recipient_account_last_four=recipient_account_last_four,
        transaction_date=transaction_date,
        description=description,
        new_balance=new_balance,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — Transfer Confirmation", html)


def send_transfer_received_email(
    to: str,
    first_name: str,
    amount: str,
    reference: str,
    sender_name: str,
    account_last_four: str,
    transaction_date: str,
    description: str,
    new_balance: str
):
    template = get_template("transfer_received.html")
    html = template.render(
        first_name=first_name,
        amount=amount,
        reference=reference,
        sender_name=sender_name,
        account_last_four=account_last_four,
        transaction_date=transaction_date,
        description=description,
        new_balance=new_balance,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — Credit Alert", html)


def send_admin_credit_email(
    to: str,
    first_name: str,
    amount: str,
    reference: str,
    sender_name: str,
    bank_name: str,
    transaction_date: str,
    description: str,
    new_balance: str
):
    template = get_template("admin_credit.html")
    html = template.render(
        first_name=first_name,
        amount=amount,
        reference=reference,
        sender_name=sender_name,
        bank_name=bank_name,
        transaction_date=transaction_date,
        description=description,
        new_balance=new_balance,
        frontend_url=settings.FRONTEND_URL,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — Account Credited", html)


def send_admin_debit_email(
    to: str,
    first_name: str,
    amount: str,
    reference: str,
    reason: str,
    transaction_date: str,
    description: str,
    new_balance: str
):
    template = get_template("admin_debit.html")
    html = template.render(
        first_name=first_name,
        amount=amount,
        reference=reference,
        reason=reason,
        transaction_date=transaction_date,
        description=description,
        new_balance=new_balance,
        frontend_url=settings.FRONTEND_URL,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — Account Debited", html)






def send_cot_bop_code_email(to: str, first_name: str, code_type: str, code: str, expires_at: str):
    html_content = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0f1115;color:#e5e7eb;border-radius:12px;overflow:hidden">
      <div style="background:#161b27;padding:32px;text-align:center;border-bottom:1px solid #2b2f36">
        <h1 style="margin:0;font-size:20px;color:#e5e7eb">Arcteron Trust</h1>
        <p style="margin:4px 0 0;font-size:12px;color:#9ca3af;letter-spacing:2px">PRIVATE BANKING & WEALTH MANAGEMENT</p>
      </div>
      <div style="padding:40px 32px">
        <p>Dear <strong>{first_name}</strong>,</p>
        <p>Your administrator has generated a <strong>{code_type}</strong> code for your account.</p>
        <div style="background:#1a1f2e;border:1px solid #2b2f36;border-radius:12px;padding:24px;text-align:center;margin:24px 0">
          <p style="margin:0 0 8px;font-size:12px;color:#9ca3af;letter-spacing:2px">{code_type} CODE</p>
          <p style="margin:0;font-size:28px;font-weight:700;letter-spacing:6px;color:#e5e7eb;font-family:monospace">{code}</p>
          <p style="margin:12px 0 0;font-size:12px;color:#9ca3af">Expires: {expires_at}</p>
        </div>
        <p style="color:#f59e0b;font-size:13px">&#9888; Never share this code with anyone. Arcteron Trust staff will never ask for it.</p>
        <p style="color:#9ca3af;font-size:13px">Use this code when prompted during your transfer to authorize the transaction.</p>
      </div>
      <div style="background:#161b27;padding:20px;text-align:center;border-top:1px solid #2b2f36">
        <p style="margin:0;font-size:12px;color:#6b7280">&copy; 2026 Arcteron Trust. All rights reserved.</p>
      </div>
    </div>
    """
    send_email(to, f"Arcteron Trust — Your {code_type} Authorization Code", html_content)
