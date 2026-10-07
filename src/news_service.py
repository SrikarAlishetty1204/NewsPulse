import html
import json
import os
import re
import sys
import time

import feedparser
import ollama
import requests
import trafilatura
from dotenv import load_dotenv

load_dotenv()

# Comma-separated lists in .env
RSS_URLS = os.getenv("RSS_URLS", "").split(",")
CATEGORIES = [name.strip() for name in os.getenv("CATEGORIES", "").split(",")]
WANTED = [name.strip() for name in os.getenv("WANTED_CATEGORIES", "").split(",")]
MODEL = os.getenv("OLLAMA_MODEL")
MAX_ENTRIES_PER_FEED = int(os.getenv("MAX_ENTRIES_PER_FEED", "5"))
# Speed settings for summarize(): trim the article (characters), cap the reply (tokens)
TRIM_TEXT = os.getenv("TRIM_TEXT", "false").lower() == "true"
TRIM_SIZE = int(os.getenv("TRIM_SIZE", "4000"))
CAP_TEXT = os.getenv("CAP_TEXT", "false").lower() == "true"
CAP_SIZE = int(os.getenv("CAP_SIZE", "300"))

# Some sites refuse requests that don't look like a browser
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
}
# Shorter than this is a paywall or consent page, not an article
MIN_ARTICLE_CHARS = 200


def ask_model(prompt, options, format=""):
    """Send one prompt to the model and return its reply text."""
    # think=False: gemma4 otherwise writes hidden reasoning before every reply
    response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}],
                           format=format, think=False, options=options)
    return response["message"]["content"]


def categorize(title, description):
    """Ask the model for one category; anything not in CATEGORIES becomes "Other"."""
    prompt = (
        "Classify this news article into exactly one of these categories: "
        + ", ".join(CATEGORIES) + ".\n"
        "Reply with the category name only, one word, nothing else.\n\n"
        f"Title: {title}\n"
    )
    if description:
        prompt += f"Description: {description}\n"

    reply = ask_model(prompt, {"temperature": 0}).strip(" \n.*\"'").lower()

    # Anything not in CATEGORIES would break the CategoryId foreign key later
    category = "Other"
    for name in CATEGORIES:
        if name.lower() == reply:
            category = name
    return category


def summarize(text):
    """Return (summary, importance 1-10), or (None, None) if the reply is unusable."""
    if TRIM_TEXT:
        text = text[:TRIM_SIZE]
    options = {"temperature": 0}
    if CAP_TEXT:
        options["num_predict"] = CAP_SIZE

    prompt = (
        "Summarize this news article in 3-4 sentences of plain prose, and rate how "
        "important it is to a general reader from 1 (trivial) to 10 (major).\n"
        'Reply with JSON only: {"summary": "...", "importance": <1-10>}\n'
        "If the text is not a news article (a menu, login page or video page), "
        'reply {"summary": "", "importance": 0}.\n\n'
        f"Article:\n{text}"
    )
    try:
        # ResponseError: the model can loop on long pages and Ollama aborts the request.
        # A reply cut off by CAP_SIZE is invalid JSON and lands in ValueError.
        reply = json.loads(ask_model(prompt, options, format="json"))
        summary = str(reply["summary"]).strip()
        importance = int(reply["importance"])
    except (ollama.ResponseError, ValueError, KeyError, TypeError):
        return None, None

    # The table has CHECK (Importance BETWEEN 1 AND 10)
    if not summary or importance < 1 or importance > 10:
        return None, None
    return summary, importance


def fetch_news(saved_urls):
    """Return categorized articles; wanted ones also get text, summary and importance."""
    # The Hindu titles contain zero-width characters that crash the default Windows console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    counts = {"seen": 0, "duplicate": 0, "gated-out": 0, "fetch-failed": 0,
              "summary-failed": 0, "summarized": 0}
    articles = []
    for rss_url in RSS_URLS:
        rss_url = rss_url.strip()
        if not rss_url:
            continue
        feed = feedparser.parse(rss_url)
        print(f"{rss_url}: {len(feed.entries)} entries, taking {MAX_ENTRIES_PER_FEED}")

        for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:
            counts["seen"] += 1
            title = entry.title

            # Checked before categorizing so a re-run costs no model calls
            if entry.link in saved_urls:
                counts["duplicate"] += 1
                print(f"{'duplicate':<11} | {'skip':<6} | {title}")
                continue

            description = html.unescape(re.sub(r"<[^>]+>", "", entry.get("description", ""))).strip()
            category = categorize(title, description)
            wanted = category in WANTED
            print(f"{category:<11} | {'wanted' if wanted else 'skip':<6} | {title}")
            print(f"{entry.link}")
            if not wanted:
                counts["gated-out"] += 1

            # Only wanted articles are downloaded; text stays None when the fetch fails
            text = None
            if wanted:
                try:
                    page = requests.get(entry.link, headers=BROWSER_HEADERS, timeout=15)
                    if page.status_code != 200:
                        print(f"fetch failed: HTTP {page.status_code}")
                    else:
                        text = trafilatura.extract(page.text, include_comments=False, include_tables=False)
                        if not text or len(text) < MIN_ARTICLE_CHARS:
                            print("fetch failed: no article text found")
                            text = None
                        else:
                            print(f"fetched {len(text.split())} words")
                except requests.RequestException as error:
                    print(f"fetch failed: {error}")
                time.sleep(1)
                if text is None:
                    counts["fetch-failed"] += 1

            summary = None
            importance = None
            if text:
                summary, importance = summarize(text)
                if summary is None:
                    counts["summary-failed"] += 1
                    print("summary failed: not an article, or no usable reply from the model")
                else:
                    counts["summarized"] += 1
                    print(f"summarized, importance {importance}")

            articles.append({
                "title": title,
                "description": description,
                "link": entry.link,
                "source": rss_url,
                "category": category,
                "wanted": wanted,
                "text": text,
                "summary": summary,
                "importance": importance
            })

    # Ollama otherwise keeps the model in RAM for 5 minutes after the last call
    ollama.generate(model=MODEL, keep_alive=0)

    print(" / ".join(f"{name} {count}" for name, count in counts.items()))
    return articles
