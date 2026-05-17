import emails
from emails.template import JinjaTemplate
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
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.APP_NAME, settings.MAIL_FROM)
    )

    response = message.send(
        to=to,
        smtp={
            "host": settings.MAIL_SERVER,
            "port": settings.MAIL_PORT,
            "tls": True,
            "user": settings.MAIL_USERNAME,
            "password": settings.MAIL_PASSWORD,
        }
    )
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





