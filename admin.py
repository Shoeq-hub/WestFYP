from database import get_connection
#w2096743


def get_pending_resources():
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.id, r.title, r.source, r.keywords, r.created_at,
               u.username AS submitted_by
        FROM resources r
        LEFT JOIN users u ON r.submitted_by = u.id
        WHERE r.status = 'pending'
        ORDER BY r.created_at ASC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def approve_resource(resource_id):
    conn = get_connection()
    resource = conn.execute(
        "SELECT id FROM resources WHERE id = ? AND status = 'pending'",
        (resource_id,)
    ).fetchone()

    if not resource:
        conn.close()
        return {"success": False, "error": "Resource not found or already processed"}

    conn.execute(
        "UPDATE resources SET status = 'approved' WHERE id = ?",
        (resource_id,)
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Resource {resource_id} approved"}


def reject_resource(resource_id):
    conn = get_connection()
    resource = conn.execute(
        "SELECT id FROM resources WHERE id = ? AND status = 'pending'",
        (resource_id,)
    ).fetchone()

    if not resource:
        conn.close()
        return {"success": False, "error": "Resource not found or already processed"}

    conn.execute(
        "DELETE FROM resources WHERE id = ?",
        (resource_id,)
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Resource {resource_id} rejected and removed"}


def add_resource_directly(title, source, content, keywords, submitted_by=None):
    """Admin can also add content directly as approved."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO resources (title, source, content, keywords, status, submitted_by)
        VALUES (?, ?, ?, ?, 'approved', ?)
    """, (title, source, content, keywords, submitted_by))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Resource added directly as approved"}
