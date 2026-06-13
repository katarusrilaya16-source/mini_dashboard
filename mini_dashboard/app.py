import re
import sqlite3
import hashlib
import os
from datetime import datetime

import streamlit as st


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

def _hash_password(password: str) -> str:
    return hashlib.sha256(f"streamlit_app_salt_{password}".encode()).hexdigest()

def _bootstrap_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            password   TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    conn.commit()
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
            ("Admin", "admin1@example.com", _hash_password("Admin@123"),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    conn.close()

_bootstrap_db()

from check_db import add_user, get_user, get_all_users, user_exists, verify_password

st.set_page_config(
    page_title="User Dashboard",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

for key, val in {
    "page": "login",
    "logged_in": False,
    "user_email": "",
    "user_name": "",
    "show_add_user": False,
    "register_success": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

def validate_email(email: str) -> str:
    email = email.strip()
    if len(email) < 4 or len(email) > 20:
        return "Email must be between 4 and 20 characters."
    if not re.search(r"\d", email):
        return "Email must contain at least one number."
    if not (email.endswith(".com") or email.endswith(".in")):
        return "Email must end with .com or .in"
    if "@" not in email:
        return "Email must contain '@'."
    return ""


def validate_password(password: str) -> str:
    if len(password) < 4 or len(password) > 20:
        return "Password must be between 4 and 20 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"\d", password):
        return "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;':\",./<>?]", password):
        return "Password must contain at least one special character."
    return ""


def mask_password(hashed: str) -> str:
    if len(hashed) <= 10:
        return "*" * len(hashed)
    return hashed[:6] + "*" * (len(hashed) - 10) + hashed[-4:]

def inject_login_css():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #1a3a6b 0%, #1565C0 50%, #0D47A1 100%);
        min-height: 100vh;
    }
    [data-testid="stHeader"] { background: transparent; }
    .auth-card {
        background: rgba(255,255,255,0.97);
        border-radius: 16px;
        padding: 48px 40px 40px 40px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.35);
        max-width: 420px;
        margin: 0 auto;
    }
    .auth-card h2 { text-align:center; color:#1565C0; margin-bottom:8px; font-size:1.8rem; font-weight:700; }
    .auth-card .subtitle { text-align:center; color:#555; margin-bottom:28px; font-size:0.92rem; }
    label { color:#333 !important; font-weight:600 !important; }
    .err-msg {
        background:#FFEBEE; color:#B71C1C; border-left:4px solid #C62828;
        border-radius:6px; padding:10px 14px; margin-top:6px; font-size:0.88rem; font-weight:500;
    }
    .ok-msg {
        background:#E8F5E9; color:#1B5E20; border-left:4px solid #2E7D32;
        border-radius:6px; padding:10px 14px; margin-top:6px; font-size:0.88rem; font-weight:500;
    }
    /* Login button — blue */
    div[data-testid="stButton"]:has(button[kind="primary"]) button {
        background:#1565C0 !important; color:white !important; border:none !important;
        border-radius:8px !important; height:46px !important; font-size:1rem !important;
        font-weight:600 !important; width:100% !important;
    }
    /* Register button — green */
    div[data-testid="stButton"]:has(button[kind="secondary"]) button {
        background:#2E7D32 !important; color:white !important; border:none !important;
        border-radius:8px !important; height:46px !important; font-size:1rem !important;
        font-weight:600 !important; width:100% !important;
    }
    </style>
    """, unsafe_allow_html=True)


def inject_dashboard_css():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background:#EEF2FF; }
    [data-testid="stHeader"] { background:#1565C0; }
    [data-testid="stSidebar"] { background:#1a3a6b !important; }
    [data-testid="stSidebar"] * { color:white !important; }
    [data-testid="stSidebar"] .stButton > button {
        background:#43A047 !important; color:white !important; border:none !important;
        border-radius:8px !important; width:100%; font-weight:600;
    }
    /* Red logout */
    .logout-btn button {
        background:#C62828 !important; color:white !important; border:none !important;
        border-radius:8px !important; font-weight:600 !important;
    }
    .user-table {
        width:100%; border-collapse:collapse; background:white;
        border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.08);
        font-size:0.93rem;
    }
    .user-table thead tr { background:#1565C0; color:white; }
    .user-table th { padding:14px 18px; text-align:left; font-weight:600; letter-spacing:0.03em; }
    .user-table td { padding:13px 18px; border-bottom:1px solid #E8EDF5; color:#2c3e50; }
    .user-table tbody tr:last-child td { border-bottom:none; }
    .user-table tbody tr:hover { background:#F5F8FF; }
    .badge-email { background:#E3F2FD; color:#1565C0; border-radius:20px; padding:3px 10px; font-size:0.83rem; }
    .badge-pass { background:#F3E5F5; color:#6A1B9A; border-radius:6px; padding:3px 10px; font-size:0.8rem; font-family:monospace; }
    .badge-time { color:#78909C; font-size:0.82rem; }
    .add-user-card { background:white; border-radius:14px; padding:28px 24px; box-shadow:0 4px 20px rgba(0,0,0,0.10); margin-bottom:28px; }
    .err-msg { background:#FFEBEE; color:#B71C1C; border-left:4px solid #C62828; border-radius:6px; padding:9px 14px; margin-top:4px; font-size:0.87rem; }
    .ok-msg  { background:#E8F5E9; color:#1B5E20; border-left:4px solid #2E7D32; border-radius:6px; padding:9px 14px; margin-top:4px; font-size:0.87rem; }
    </style>
    """, unsafe_allow_html=True)

def page_login():
    inject_login_css()
    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<h2>🔐 Welcome Back</h2>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Sign in to your account</p>', unsafe_allow_html=True)

        if st.session_state.register_success:
            st.markdown('<div class="ok-msg">✅ Account created! Please log in.</div>', unsafe_allow_html=True)
            st.session_state.register_success = False

        email    = st.text_input("Email",    placeholder="you1@example.com", key="login_email")
        password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        login_clicked    = st.button("Login",                        key="btn_login",       use_container_width=True, type="primary")
        register_clicked = st.button("Register — Create an Account", key="btn_go_register", use_container_width=True, type="secondary")

        st.markdown("</div>", unsafe_allow_html=True)

        if login_clicked:
            email_err = validate_email(email)
            pass_err  = validate_password(password)
            if email_err:
                st.markdown(f'<div class="err-msg">📧 {email_err}</div>', unsafe_allow_html=True)
            elif pass_err:
                st.markdown(f'<div class="err-msg">🔑 {pass_err}</div>', unsafe_allow_html=True)
            else:
                user = get_user(email)
                if user is None:
                    st.markdown('<div class="err-msg">❌ No account found with that email. Please register first.</div>', unsafe_allow_html=True)
                elif not verify_password(password, user["password"]):
                    st.markdown('<div class="err-msg">❌ Incorrect password. Please try again.</div>', unsafe_allow_html=True)
                else:
                    st.session_state.logged_in  = True
                    st.session_state.user_email = user["email"]
                    st.session_state.user_name  = user["name"]
                    st.session_state.page       = "dashboard"
                    st.rerun()

        if register_clicked:
            st.session_state.page = "register"
            st.rerun()

def page_register():
    inject_login_css()
    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown('<h2>📝 Create Account</h2>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Register a new account</p>', unsafe_allow_html=True)

        reg_email    = st.text_input("Email",    placeholder="you1@example.com", key="reg_email")
        reg_password = st.text_input("Password", type="password", placeholder="Min 4 chars, 1 upper, 1 number, 1 special", key="reg_pass")

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        
        st.markdown(
            "<div style='font-size:0.78rem; color:#888; margin-bottom:12px;'>"
            "💡 e.g. <b>Laya@123</b> — uppercase + number + special character</div>",
            unsafe_allow_html=True,
        )

        submit_clicked = st.button("Create Account", key="btn_register_submit", use_container_width=True, type="primary")
        back_clicked   = st.button("← Back to Login", key="btn_back_login",    use_container_width=True, type="secondary")

        st.markdown("</div>", unsafe_allow_html=True)

        if submit_clicked:
            email_err = validate_email(reg_email)
            pass_err  = validate_password(reg_password)

            if email_err:
                st.markdown(f'<div class="err-msg">📧 {email_err}</div>', unsafe_allow_html=True)
            elif pass_err:
                st.markdown(f'<div class="err-msg">🔑 {pass_err}</div>', unsafe_allow_html=True)
            elif user_exists(reg_email):
                st.markdown('<div class="err-msg">⚠️ This email is already registered. Please login instead.</div>', unsafe_allow_html=True)
            else:
                display_name = reg_email.split("@")[0].capitalize()
                success, err = add_user(display_name, reg_email, reg_password)
                if success:
                    st.session_state.register_success = True
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.markdown(
                        f'<div class="err-msg">❌ Registration failed: {err if err else "Unknown error. Please try again."}</div>',
                        unsafe_allow_html=True,
                    )

        if back_clicked:
            st.session_state.page = "login"
            st.rerun()



def page_dashboard():
    inject_dashboard_css()

    with st.sidebar:
        st.markdown(
            f"<div style='padding:16px 0 24px 0; font-size:1.1rem; font-weight:700;'>"
            f"👋 Hello, {st.session_state.user_name}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        if st.button("➕  Add User", key="sidebar_add_user", use_container_width=True):
            st.session_state.show_add_user = not st.session_state.show_add_user

    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown("<h2 style='color:#1565C0; margin-bottom:0;'>📊 Welcome to Dashboard</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#546E7A; margin-top:4px;'>Logged in as <strong>{st.session_state.user_email}</strong></p>", unsafe_allow_html=True)
    with top_right:
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("🚪 Logout", key="btn_logout", use_container_width=True):
            for k in ["logged_in","user_email","user_name","show_add_user"]:
                st.session_state[k] = False if k == "logged_in" or k == "show_add_user" else ""
            st.session_state.page = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    if st.session_state.show_add_user:
        st.markdown('<div class="add-user-card">', unsafe_allow_html=True)
        st.markdown("### ➕ Add New User")
        c1, c2, c3 = st.columns(3)
        with c1: new_name  = st.text_input("Name",     placeholder="Jane Doe",          key="add_name")
        with c2: new_email = st.text_input("Email",    placeholder="jane1@example.com", key="add_email")
        with c3: new_pass  = st.text_input("Password", type="password", placeholder="Jane@123", key="add_pass")

        s_col, c_col, _ = st.columns([1, 1, 4])
        with s_col: save_clicked   = st.button("💾 Save",   key="btn_save",   use_container_width=True)
        with c_col: cancel_clicked = st.button("✖ Cancel", key="btn_cancel", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if save_clicked:
            name_err  = "" if new_name.strip() else "Name is required."
            email_err = validate_email(new_email)
            pass_err  = validate_password(new_pass)
            if name_err:
                st.markdown(f'<div class="err-msg">👤 {name_err}</div>', unsafe_allow_html=True)
            elif email_err:
                st.markdown(f'<div class="err-msg">📧 {email_err}</div>', unsafe_allow_html=True)
            elif pass_err:
                st.markdown(f'<div class="err-msg">🔑 {pass_err}</div>', unsafe_allow_html=True)
            elif user_exists(new_email):
                st.markdown('<div class="err-msg">⚠️ A user with this email already exists.</div>', unsafe_allow_html=True)
            else:
                success, err = add_user(new_name.strip(), new_email, new_pass)
                if success:
                    st.markdown('<div class="ok-msg">✅ User added successfully!</div>', unsafe_allow_html=True)
                    st.session_state.show_add_user = False
                    st.rerun()
                else:
                    st.markdown(f'<div class="err-msg">❌ Failed: {err}</div>', unsafe_allow_html=True)

        if cancel_clicked:
            st.session_state.show_add_user = False
            st.rerun()

  
    st.markdown("### 👥 All Users")
    users = get_all_users()

    if not users:
        st.info("No users found.")
    else:
        rows_html = ""
        for u in users:
            rows_html += f"""
            <tr>
                <td><strong>{u['name']}</strong></td>
                <td><span class='badge-email'>{u['email']}</span></td>
                <td><span class='badge-pass'>{mask_password(u['password'])}</span></td>
                <td><span class='badge-time'>🕒 {u['created_at']}</span></td>
            </tr>"""
        st.markdown(f"""
        <table class="user-table">
            <thead><tr><th>Name</th><th>Email</th><th>Password (masked)</th><th>Created Time</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        <p style='color:#90A4AE; font-size:0.82rem; margin-top:10px;'>Showing {len(users)} user(s)</p>
        """, unsafe_allow_html=True)

def main():
    if not st.session_state.logged_in and st.session_state.page == "dashboard":
        st.session_state.page = "login"

    if   st.session_state.page == "login":     page_login()
    elif st.session_state.page == "register":  page_register()
    elif st.session_state.page == "dashboard": page_dashboard()
    else:
        st.session_state.page = "login"
        st.rerun()

if __name__ == "__main__":
    main()