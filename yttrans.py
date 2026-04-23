from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from sklearn.feature_extraction.text import TfidfVectorizer
from deep_translator import GoogleTranslator
from langdetect import detect
import re
import yt_dlp
#w2096743


def extract_video_id(video_url):
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]+)", video_url)
    return match.group(1) if match else video_url


def translate_to_english(text):
    """Translate text to English if it is not already in English."""
    try:
        if detect(text) == "en":
            return text
    except Exception:
        pass

    try:
        # GoogleTranslator has a 5000 char limit per call so chunk if needed
        chunk_size = 4500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        translated_chunks = [
            GoogleTranslator(source="auto", target="en").translate(chunk)
            for chunk in chunks
        ]
        return " ".join(translated_chunks)
    except Exception as e:
        print(f"[WARN] Translation failed, using original text: {e}")
        return text


def extract_keywords(text, top_k=10):
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=top_k
    )
    vectorizer.fit([text])
    return " ".join(vectorizer.get_feature_names_out())


def get_transcript(video_id):
    """
    Try to fetch English transcript first.
    Fall back to any available language and translate.
    """
    api = YouTubeTranscriptApi()

    # Try English first
    try:
        transcript = api.fetch(video_id, languages=["en"])
        formatter = TextFormatter()
        return formatter.format_transcript(transcript).lower()
    except Exception:
        pass

    # Fall back to any language then translate
    try:
        transcript = api.fetch(video_id)
        formatter = TextFormatter()
        raw_text = formatter.format_transcript(transcript).lower()
        print(" !!! Non-English transcript detected, translating...")
        return translate_to_english(raw_text)
    except Exception as e:
        raise RuntimeError(f"Could not fetch transcript: {e}")


def get_video_title(url):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title", "Unknown title")


def transcript_to_row(video_url):
    video_id = extract_video_id(video_url)

    text = get_transcript(video_id)
    keywords = extract_keywords(text)

    title = "Unknown title"
    try:
        raw_title = get_video_title(video_url)
        title = translate_to_english(raw_title)
    except Exception as e:
        print(f"[WARN] Could not fetch title: {e}")

    return {
        "resource_id": video_id,
        "title": title,
        "source": video_url,
        "content": text,
        "keywords": keywords
    }


# Kept for standalone testing
if __name__ == "__main__":
    df = transcript_to_row("https://youtu.be/QoIRX37VZpo?si=s0mqdUrvfDiIw7Xk")
    print(df)
