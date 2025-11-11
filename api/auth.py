# api/auth.py
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import json

# Core imports
from core.security import hash_password, verify_password
from core.token_utils import create_access_token
from core.email_utils import create_email_token, send_verification_email, verify_email_token

router = APIRouter()

# -------------------------------
# User Database (local JSON)
# -------------------------------
USER_DB = Path("data/users.json")
USER_DB.parent.mkdir(exist_ok=True)
if not USER_DB.exists():
    USER_DB.write_text("[]")

def load_users():
    try:
        return json.loads(USER_DB.read_text())
    except Exception:
        return []

def save_users(users):
    USER_DB.write_text(json.dumps(users, indent=2))

def find_user(username):
    for u in load_users():
        if u["username"] == username:
            return u
    return None

def find_user_by_email(email):
    for u in load_users():
        if u["email"] == email:
            return u
    return None


# -------------------------------
# Authentication Check
# -------------------------------
def is_authenticated(request: Request):
    """Check if user session is valid."""
    return request.session.get("user") is not None


# -------------------------------
# Registration (GET + POST)
# -------------------------------
@router.get("/register", response_class=HTMLResponse)
async def register_page():
    """Render registration form."""
    return Path("api/web_ui/register.html").read_text()


@router.post("/register")
async def register_user(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    """Handle user registration and send email verification link."""
    users = load_users()

    if find_user(username) or find_user_by_email(email):
        return HTMLResponse("<h3>User already exists. <a href='/register'>Try again</a></h3>")

    # Hash password and create user record
    new_user = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "verified": False
    }

    users.append(new_user)
    save_users(users)

    # Generate verification token
    token = create_email_token(email)

    # Send verification email (async, using aiosmtplib)
    await send_verification_email(email, token)

    return HTMLResponse(
        "<h3>✅ Registration successful! Please check your email for the verification link.</h3>"
        "<p><a href='/login'>Return to login</a></p>"
    )


# -------------------------------
# Email Verification
# -------------------------------
@router.get("/verify-email/{token}")
async def verify_email(token: str):
    """Verify email using token sent to user."""
    email = verify_email_token(token)
    if not email:
        return HTMLResponse("<h3>❌ Invalid or expired verification link.</h3><p><a href='/login'>Back to login</a></p>")

    users = load_users()
    for u in users:
        if u["email"] == email:
            u["verified"] = True
            save_users(users)
            # Auto-redirect to login with success message
            html = """
            <html>
              <head><meta http-equiv="refresh" content="3;url=/login" /></head>
              <body style="font-family:sans-serif;text-align:center;margin-top:60px;">
                <h3>✅ Email verified successfully!</h3>
                <p>You will be redirected to the login page shortly.</p>
                <p>If not, <a href="/login">click here</a>.</p>
              </body>
            </html>
            """
            return HTMLResponse(html)
    return HTMLResponse("<h3>❌ User not found. Please register again.</h3>")


# -------------------------------
# Login (GET + POST)
# -------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page."""
    return """
    <html>
    <head><title>Login</title></head>
    <body style="font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;">
      <form action="/login" method="post" style="background:#f7f9fc;padding:30px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.1)">
        <h2>Matter Gateway Login</h2>
        <label>Username:</label><br>
        <input name="username" required><br><br>
        <label>Password:</label><br>
        <input type="password" name="password" required><br><br>
        <button type="submit">Login</button>
        <p>Don't have an account? <a href="/register">Register here</a></p>
      </form>
    </body>
    </html>
    """


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Validate user credentials and issue JWT."""
    user = find_user(username)
    if not user:
        return HTMLResponse("<h3>❌ User not found. <a href='/login'>Try again</a></h3>")

    if not user.get("verified"):
        return HTMLResponse("<h3>⚠️ Email not verified! Please verify before logging in.</h3>")

    if not verify_password(password, user["password_hash"]):
        return HTMLResponse("<h3>❌ Invalid password. <a href='/login'>Try again</a></h3>")

    # ✅ Create session + JWT cookie
    request.session["user"] = username
    token = create_access_token(username)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,       # set True when using HTTPS
        samesite="lax",
        max_age=3600,
    )
    return response


# -------------------------------
# Logout
# -------------------------------
@router.get("/logout")
async def logout(request: Request):
    """Clear session and token cookie."""
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response
