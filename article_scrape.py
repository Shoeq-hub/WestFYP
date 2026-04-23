import hashlib
import requests
import trafilatura
from sklearn.feature_extraction.text import TfidfVectorizer
from deep_translator import GoogleTranslator
from langdetect import detect
#w2096743


def get_resource_id(url):
    """Generate a unique ID from the URL using MD5 hash."""
    return hashlib.md5(url.encode()).hexdigest()


def translate_to_english(text):
    """Translate text to English if it is not already in English."""
    try:
        if detect(text) == "en":
            return text
    except Exception:
        pass

    try:
        chunk_size = 4500
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        translated_chunks = [
            GoogleTranslator(source="auto", target="en").translate(chunk)
            for chunk in chunks
        ]
        return " ".join(translated_chunks)
    except Exception as e:
        print(f"[WARN] Translation failed, using original text: {e}")
        return text


def extract_keywords(text, top_k=10):
    vectorizer = TfidfVectorizer(stop_words="english", max_features=top_k)
    vectorizer.fit([text])
    return " ".join(vectorizer.get_feature_names_out())


def scrape_full_text(url):
    """Tier 1: Try trafilatura for full article text."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text.strip()) > 100:
                return text.strip()
    except Exception as e:
        print(f"[WARN] trafilatura failed: {e}")
    return None


def scrape_opengraph(url):
    """Tier 2: Fall back to OpenGraph metadata (title + description)."""
    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0"
        })
        html = response.text

        title = ""
        description = ""

        # Extract og:title
        for tag in ['og:title', 'twitter:title']:
            match = _meta_content(html, tag)
            if match:
                title = match
                break

        # Extract og:description
        for tag in ['og:description', 'twitter:description', 'description']:
            match = _meta_content(html, tag)
            if match:
                description = match
                break

        combined = f"{title}. {description}".strip()
        if len(combined) > 10:
            return title or "Unknown title", combined

    except Exception as e:
        print(f"[WARN] OpenGraph scrape failed: {e}")

    return None, None


def _meta_content(html, property_name):
    """Helper to extract content from a meta tag by property or name."""
    import re
    pattern = rf'<meta[^>]+(?:property|name)=["\']{{0,1}}{re.escape(property_name)}["\']{{0,1}}[^>]+content=["\']([^"\']+)["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try reversed attribute order
    pattern2 = rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{{0,1}}{re.escape(property_name)}["\']{{0,1}}'
    match2 = re.search(pattern2, html, re.IGNORECASE)
    return match2.group(1).strip() if match2 else None


def article_to_row(url):
    """
    Main function. Tries full scrape, falls back to OpenGraph.
    Raises RuntimeError if both fail (user should paste text manually).
    """
    resource_id = get_resource_id(url)
    title = "Unknown title"
    content = None

    # Tier 1: Full text via trafilatura
    full_text = scrape_full_text(url)
    if full_text:
        content = full_text
        # Try to get title from OpenGraph even if we have full text
        og_title, _ = scrape_opengraph(url)
        if og_title:
            title = og_title
        print("[INFO] Full article text extracted via trafilatura")

    # Tier 2: OpenGraph fallback
    if not content:
        og_title, og_text = scrape_opengraph(url)
        if og_text:
            title = og_title or "Unknown title"
            content = og_text
            print("[INFO] Partial metadata extracted via OpenGraph")

    # Tier 3: Both failed
    if not content:
        raise RuntimeError(
            "Could not extract content from this URL. "
            "The site may block scraping. Please paste the article text manually."
        )

    content = translate_to_english(content)
    title = translate_to_english(title)
    keywords = extract_keywords(content)

    return {
        "resource_id": resource_id,
        "title": title,
        "source": url,
        "content": content,
        "keywords": keywords
    }


if __name__ == "__main__":
    url = input("Enter article URL: ")
    row = article_to_row(url)
    print(f"\nTitle:    {row['title']}")
    print(f"Keywords: {row['keywords']}")
    print(f"Content preview: {row['content'][:300]}...")
