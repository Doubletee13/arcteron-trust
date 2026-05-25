from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
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
    sg = SendGridAPIClient(api_key=settings.MAIL_PASSWORD)
    message = Mail(
        from_email=(settings.MAIL_FROM, settings.APP_NAME),
        to_emails=to,
        subject=subject,
        html_content=html_content
    )
    response = sg.send(message)
    print(f"EMAIL TO: {to} | STATUS: {response.status_code} | BODY: {response.body}")
    return response


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


def send_verification_email(to: str, first_name: str, token: str):
    verification_url = f"{settings.FRONTEND_URL}/pages/verify-email.html?token={token}"
    template = get_template("email_verification.html")
    html = template.render(
        first_name=first_name,
        verification_url=verification_url,
        frontend_url=settings.FRONTEND_URL,
        year=datetime.utcnow().year
    )
    send_email(to, f"{settings.APP_NAME} — Verify Your Email Address", html)


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





