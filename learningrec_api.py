from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from database import init_db, get_connection
from auth import register_user, login_user, get_user_by_id
from feedback import (
    save_feedback, get_user_feedback,
    save_to_history, get_user_history,
    save_bookmark, get_user_bookmarks,
    remove_bookmark, clear_history, remove_feedback
)
from admin import get_pending_resources, approve_resource, reject_resource
from learningrec import recommend_resources
from yttrans import transcript_to_row
from article_scrape import article_to_row
#w2096743

app = Flask(__name__)
app.secret_key = "fyp-learning-curator-secret"

init_db()


# --- Helpers ---

def get_session_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_session_user():
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_session_user()
        if not user:
            return redirect(url_for("login_page"))
        if not user["is_admin"]:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    """For JSON API routes only."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_session_user():
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return decorated


def api_admin_required(f):
    """For JSON API routes only."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_session_user()
        if not user:
            return jsonify({"error": "Login required"}), 401
        if not user["is_admin"]:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_user():
    """Makes current_user available in all templates."""
    return {"current_user": get_session_user()}


def is_youtube_url(url):
    return "youtube.com" in url or "youtu.be" in url


# ============================================================
# PAGE ROUTES (render HTML)
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login_page():
    if get_session_user():
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/register")
def register_page():
    if get_session_user():
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/resources")
def resources_page():
    return render_template("resources.html")


@app.route("/my-submissions")
@login_required
def submissions_page():
    return render_template("submissions.html")


@app.route("/bookmarks")
@login_required
def bookmarks_page():
    return render_template("bookmarks.html")


@app.route("/history")
@login_required
def history_page():
    return render_template("history.html")


@app.route("/likes")
@login_required
def likes_page():
    return render_template("likes.html")


@app.route("/account")
@login_required
def account_page():
    return render_template("account.html")


@app.route("/admin")
@login_required
def admin_page():
    user = get_session_user()
    if not user["is_admin"]:
        return redirect(url_for("index"))
    return render_template("admin.html")


# ============================================================
# API ROUTES (return JSON, called by JavaScript)
# ============================================================

# --- Auth ---

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    result = register_user(username, password)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 409
    return jsonify(result), 201


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    result = login_user(username, password)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 401

    session["user_id"] = result["user_id"]
    return jsonify({
        "message": "Logged in",
        "user_id": result["user_id"],
        "username": result["username"],
        "is_admin": result["is_admin"]
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"})


# --- Recommend ---

@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    data = request.json
    preferences = data.get("preferences", "").strip()
    my_submissions_only = data.get("my_submissions_only", False)

    if not preferences:
        return jsonify({"error": "Preferences required"}), 400

    user = get_session_user()
    user_id = user["id"] if user else None

    # my_submissions_only only works when logged in
    if my_submissions_only and not user_id:
        return jsonify({"error": "Login required to filter by your submissions"}), 401

    # Warn if user has too few approved submissions
    if my_submissions_only and user_id:
        conn = get_connection()
        count = conn.execute("""
            SELECT COUNT(*) as c FROM resources
            WHERE submitted_by = ? AND status = 'approved'
        """, (user_id,)).fetchone()["c"]
        conn.close()
        if count < 3:
            return jsonify({
                "warning": True,
                "message": f"You only have {count} approved submission(s). Recommendations may be limited.",
                "results": recommend_resources(preferences, user_id=user_id, my_submissions_only=True)
            })

    results = recommend_resources(preferences, user_id=user_id, my_submissions_only=my_submissions_only)
    return jsonify(results)


# --- Submit URL ---

@app.route("/api/submit", methods=["POST"])
@api_login_required
def api_submit():
    data = request.json
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "URL required"}), 400

    user = get_session_user()

    try:
        if is_youtube_url(url):
            row = transcript_to_row(url)
        else:
            row = article_to_row(url)
    except Exception as e:
        return jsonify({"error": f"Could not process URL: {str(e)}"}), 400

    conn = get_connection()
    existing = conn.execute(
        "SELECT id, status FROM resources WHERE resource_id = ?",
        (row["resource_id"],)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({"error": f"This resource already exists (status: {existing['status']})"}), 409

    conn.execute("""
        INSERT INTO resources (resource_id, title, source, content, keywords, status, submitted_by)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (row["resource_id"], row["title"], row["source"], row["content"], row["keywords"], user["id"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Submitted for admin review"}), 201


# --- My Submissions ---

@app.route("/api/my-submissions", methods=["GET"])
@api_login_required
def api_my_submissions():
    user = get_session_user()
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, resource_id, title, source, status, created_at
        FROM resources
        WHERE submitted_by = ?
        ORDER BY created_at DESC
    """, (user["id"],)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


# --- Resources ---

@app.route("/api/resources", methods=["GET"])
def api_resources():
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, title, source, keywords, created_at
        FROM resources
        WHERE status = 'approved'
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


# --- Feedback ---

@app.route("/api/feedback", methods=["POST"])
@api_login_required
def api_save_feedback():
    data = request.json
    resource_id = data.get("resource_id")
    rating = data.get("rating")

    if resource_id is None or rating not in (1, -1):
        return jsonify({"error": "resource_id and rating (1 or -1) required"}), 400

    user = get_session_user()
    result = save_feedback(user["id"], resource_id, rating)
    return jsonify(result)


@app.route("/api/feedback", methods=["GET"])
@api_login_required
def api_get_feedback():
    user = get_session_user()
    return jsonify(get_user_feedback(user["id"]))


@app.route("/api/feedback/remove", methods=["POST"])
@api_login_required
def api_remove_feedback():
    data = request.json
    resource_id = data.get("resource_id")
    if not resource_id:
        return jsonify({"error": "resource_id required"}), 400
    user = get_session_user()
    result = remove_feedback(user["id"], resource_id)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 404
    return jsonify(result)


# --- History ---

@app.route("/api/history", methods=["POST"])
@api_login_required
def api_log_history():
    data = request.json
    resource_id = data.get("resource_id")
    if not resource_id:
        return jsonify({"error": "resource_id required"}), 400
    user = get_session_user()
    save_to_history(user["id"], resource_id)
    return jsonify({"message": "History saved"})


@app.route("/api/history", methods=["GET"])
@api_login_required
def api_get_history():
    user = get_session_user()
    return jsonify(get_user_history(user["id"]))


@app.route("/api/history/clear", methods=["POST"])
@api_login_required
def api_clear_history():
    data = request.json or {}
    if not data.get("confirm", False):
        return jsonify({
            "warning": "Clearing your history will reset your personalised recommendations. Send { \"confirm\": true } to proceed."
        }), 200
    user = get_session_user()
    return jsonify(clear_history(user["id"]))


# --- Bookmarks ---

@app.route("/api/bookmark", methods=["POST"])
@api_login_required
def api_save_bookmark():
    data = request.json
    resource_id = data.get("resource_id")
    if not resource_id:
        return jsonify({"error": "resource_id required"}), 400
    user = get_session_user()
    result = save_bookmark(user["id"], resource_id)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 409
    return jsonify(result)


@app.route("/api/bookmarks", methods=["GET"])
@api_login_required
def api_get_bookmarks():
    user = get_session_user()
    return jsonify(get_user_bookmarks(user["id"]))


@app.route("/api/bookmarks/remove", methods=["POST"])
@api_login_required
def api_remove_bookmark():
    data = request.json
    resource_id = data.get("resource_id")
    if not resource_id:
        return jsonify({"error": "resource_id required"}), 400
    user = get_session_user()
    result = remove_bookmark(user["id"], resource_id)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 404
    return jsonify(result)


# --- Change Password ---

@app.route("/api/change-password", methods=["POST"])
@api_login_required
def api_change_password():
    from werkzeug.security import check_password_hash, generate_password_hash

    data = request.json
    old_password = data.get("old_password", "").strip()
    new_password = data.get("new_password", "").strip()

    if not old_password or not new_password:
        return jsonify({"error": "old_password and new_password required"}), 400

    user = get_session_user()
    conn = get_connection()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id = ?", (user["id"],)
    ).fetchone()

    if not check_password_hash(row["password_hash"], old_password):
        conn.close()
        return jsonify({"error": "Old password is incorrect"}), 401

    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user["id"])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Password changed successfully"})


# --- Forgot Password ---

@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    data = request.json
    username = data.get("username", "").strip()

    if not username:
        return jsonify({"error": "Username required"}), 400

    conn = get_connection()
    user = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Username not found"}), 404

    conn.execute(
        "INSERT INTO reset_requests (user_id) VALUES (?)", (user["id"],)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Reset request submitted"})


# --- Admin ---

@app.route("/api/admin/reset-requests", methods=["GET"])
@api_admin_required
def api_reset_requests():
    conn = get_connection()
    rows = conn.execute("""
        SELECT rr.id, rr.requested_at, u.username, u.id as user_id
        FROM reset_requests rr
        JOIN users u ON rr.user_id = u.id
        ORDER BY rr.requested_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/admin/reset-password", methods=["POST"])
@api_admin_required
def api_admin_reset_password():
    from werkzeug.security import generate_password_hash

    data = request.json
    user_id = data.get("user_id")
    new_password = data.get("new_password", "").strip()

    if not user_id or not new_password:
        return jsonify({"error": "user_id and new_password required"}), 400

    conn = get_connection()
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user_id)
    )
    conn.execute(
        "DELETE FROM reset_requests WHERE user_id = ?", (user_id,)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Password reset successfully"})


@app.route("/api/admin/pending", methods=["GET"])
@api_admin_required
def api_pending():
    return jsonify(get_pending_resources())


@app.route("/api/admin/approve/<int:resource_id>", methods=["POST"])
@api_admin_required
def api_approve(resource_id):
    result = approve_resource(resource_id)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 404
    return jsonify(result)


@app.route("/api/admin/reject/<int:resource_id>", methods=["POST"])
@api_admin_required
def api_reject(resource_id):
    result = reject_resource(resource_id)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 404
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=False)
