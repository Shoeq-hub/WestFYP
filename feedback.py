from database import get_connection
#w2096743

# rating: 1 = like, -1 = dislike


def save_feedback(user_id, resource_id, rating):
    conn = get_connection()
    cursor = conn.cursor()

    # If feedback already exists for this user+resource, update it
    cursor.execute("""
        INSERT INTO feedback (user_id, resource_id, rating)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, resource_id) DO UPDATE SET rating = excluded.rating
    """, (user_id, resource_id, rating))

    conn.commit()
    conn.close()
    return {"success": True, "message": "Feedback saved"}


def get_user_feedback(user_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT f.resource_id, f.rating, r.title, r.keywords, r.source
        FROM feedback f
        JOIN resources r ON f.resource_id = r.id
        WHERE f.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def build_feedback_profile(user_id):
    """
    Builds a weighted preference string from user feedback.
    Liked resources contribute positively, disliked ones are excluded.
    This string is used by the recommendation engine as extra user context.
    """
    feedback_list = get_user_feedback(user_id)

    liked_keywords = []
    for item in feedback_list:
        if item["rating"] == 1:
            liked_keywords.append(item["keywords"])

    return " ".join(liked_keywords)


def save_to_history(user_id, resource_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO history (user_id, resource_id) VALUES (?, ?)",
        (user_id, resource_id)
    )
    conn.commit()
    conn.close()


def get_user_history(user_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT h.viewed_at, r.id, r.title, r.source
        FROM history h
        JOIN resources r ON h.resource_id = r.id
        WHERE h.user_id = ?
        ORDER BY h.viewed_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_bookmark(user_id, resource_id):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO bookmarks (user_id, resource_id) VALUES (?, ?)",
            (user_id, resource_id)
        )
        conn.commit()
        result = {"success": True, "message": "Bookmarked"}
    except Exception:
        result = {"success": False, "error": "Already bookmarked"}
    conn.close()
    return result


def get_user_bookmarks(user_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.saved_at, r.id, r.title, r.source
        FROM bookmarks b
        JOIN resources r ON b.resource_id = r.id
        WHERE b.user_id = ?
        ORDER BY b.saved_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def remove_bookmark(user_id, resource_id):
    conn = get_connection()
    deleted = conn.execute(
        "DELETE FROM bookmarks WHERE user_id = ? AND resource_id = ?",
        (user_id, resource_id)
    ).rowcount
    conn.commit()
    conn.close()
    if deleted:
        return {"success": True, "message": "Bookmark removed"}
    return {"success": False, "error": "Bookmark not found"}


def remove_feedback(user_id, resource_id):
    conn = get_connection()
    deleted = conn.execute(
        "DELETE FROM feedback WHERE user_id = ? AND resource_id = ?",
        (user_id, resource_id)
    ).rowcount
    conn.commit()
    conn.close()
    if deleted:
        return {"success": True, "message": "Feedback removed"}
    return {"success": False, "error": "Feedback not found"}


def clear_history(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "History cleared"}
