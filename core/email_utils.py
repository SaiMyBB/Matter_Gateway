# core/email_utils.py
import os
import jwt
import datetime
import aiosmtplib
from email.message import EmailMessage

SECRET_KEY = os.getenv("EMAIL_SECRET", "email-secret-key")
ALGORITHM = "HS256"
EMAIL_TOKEN_EXPIRE_MINUTES = 30

# --- Configure SMTP ---
SMTP_USER = os.getenv("SMTP_USER", "sainarsimhareddy11@gmail.com")
SMTP_PASS = os.getenv("SMTP_PASS", "koeomoqhkgsmgnei")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def create_email_token(email: str) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=EMAIL_TOKEN_EXPIRE_MINUTES)
    payload = {"email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_email_token(token: str):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded.get("email")
    except Exception:
        return None

async def send_verification_email(email: str, token: str):
    """Send verification email using aiosmtplib (async)."""
    verify_url = f"http://localhost:8000/verify-email/{token}"

    message = EmailMessage()
    message["From"] = SMTP_USER
    message["To"] = email
    message["Subject"] = "Verify your Matter Gateway account"
    message.set_content(f"""
    Welcome to Matter Gateway!
    Please verify your account by clicking the link below:

    {verify_url}

    (This link expires in {EMAIL_TOKEN_EXPIRE_MINUTES} minutes.)
    """)

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_SERVER,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASS,
        )
        print(f"✅ Verification email sent to {email}")
    except Exception as e:
        print(f"⚠️ Email sending failed, fallback to console output.")
        print(f"🔗 Verification link: {verify_url}")
        print(f"Error: {e}")
