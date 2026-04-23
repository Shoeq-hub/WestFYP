from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection
#w2096743


def register_user(username, password, is_admin=0):
    conn = get_connection()
    cursor = conn.cursor()

    existing = cursor.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()

    if existing:
        conn.close()
        return {"success": False, "error": "Username already taken"}

    password_hash = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
        (username, password_hash, is_admin)
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": "User registered successfully"}


def login_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    conn.close()

    if not user:
        return {"success": False, "error": "User not found"}

    if not check_password_hash(user["password_hash"], password):
        return {"success": False, "error": "Incorrect password"}

    return {
        "success": True,
        "user_id": user["id"],
        "username": user["username"],
        "is_admin": user["is_admin"]
    }


def get_user_by_id(user_id):
    conn = get_connection()
    user = conn.execute(
        "SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None
