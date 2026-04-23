import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import get_connection
#w2096743


def load_approved_resources(submitted_by=None):
    conn = get_connection()
    if submitted_by:
        rows = conn.execute("""
            SELECT id, title, source, content, keywords
            FROM resources
            WHERE status = 'approved' AND submitted_by = ?
        """, (submitted_by,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, title, source, content, keywords
            FROM resources
            WHERE status = 'approved'
        """).fetchall()
    conn.close()
    return pd.DataFrame([dict(row) for row in rows])


def recommend_resources(user_preferences, user_id=None, top_n=5, my_submissions_only=False):
    from feedback import build_feedback_profile

    submitted_by = user_id if my_submissions_only else None
    df = load_approved_resources(submitted_by=submitted_by)

    if df.empty:
        return []

    df["combined_text"] = df["keywords"] + " " + df["content"]

    # Blend user preferences with their feedback profile if logged in
    query = user_preferences.lower()
    if user_id:
        feedback_profile = build_feedback_profile(user_id)
        if feedback_profile:
            query = query + " " + feedback_profile

    documents = [query] + df["combined_text"].tolist()

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(documents)

    similarity_scores = cosine_similarity(
        tfidf_matrix[0:1],
        tfidf_matrix[1:]
    ).flatten()

    df["similarity"] = similarity_scores

    recommendations = df.sort_values(by="similarity", ascending=False)

    return recommendations.head(top_n)[
        ["id", "title", "source", "keywords", "similarity"]
    ].to_dict(orient="records")
