import html
import os
import re
import sys

import feedparser
import ollama
from dotenv import load_dotenv

load_dotenv()

# Comma-separated lists in .env
RSS_URLS = os.getenv("RSS_URLS", "").split(",")
CATEGORIES = [name.strip() for name in os.getenv("CATEGORIES", "").split(",")]
WANTED = [name.strip() for name in os.getenv("WANTED_CATEGORIES", "").split(",")]
MODEL = os.getenv("OLLAMA_MODEL")
MAX_ENTRIES_PER_FEED = int(os.getenv("MAX_ENTRIES_PER_FEED", "5"))

def fetch_news():
    # The Hindu titles contain zero-width characters that crash the default Windows console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    articles = []
    for rss_url in RSS_URLS:
        rss_url = rss_url.strip()
        if not rss_url:
            continue
        feed = feedparser.parse(rss_url)
        print(f"{rss_url}: {len(feed.entries)} entries, taking {MAX_ENTRIES_PER_FEED}")

        for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:
            title = entry.title
            description = html.unescape(re.sub(r"<[^>]+>", "", entry.get("description", ""))).strip()

            prompt = (
                "Classify this news article into exactly one of these categories: "
                + ", ".join(CATEGORIES) + ".\n"
                "Reply with the category name only, one word, nothing else.\n\n"
                f"Title: {title}\n"
            )
            if description:
                prompt += f"Description: {description}\n"

            response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
            reply = response["message"]["content"].strip(" \n.*\"'").lower()

            # Anything not in CATEGORIES would break the CategoryId foreign key later
            category = "Other"
            for name in CATEGORIES:
                if name.lower() == reply:
                    category = name

            wanted = category in WANTED
            print(f"{category:<11} | {'wanted' if wanted else 'skip':<6} | {title}")

            articles.append({
                "title": title,
                "description": description,
                "link": entry.link,
                "source": rss_url,
                "category": category,
                "wanted": wanted
            })

    print("Total articles:", len(articles))
    return articles


if __name__ == "__main__":
    fetch_news()
