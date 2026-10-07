import os

from src.news_service import fetch_news

OUTPUT_FILE = "output/articles.txt"

if __name__ == "__main__":
    # Empty set: process every entry, even ones already in the database
    articles = fetch_news(set())

    # Test output: everything fetched, in a file you can read
    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for article in articles:
            out.write(f"TITLE:    {article['title']}\n")
            out.write(f"URL:      {article['link']}\n")
            out.write(f"CATEGORY: {article['category']} ({'wanted' if article['wanted'] else 'skipped'})\n")
            if article["summary"]:
                out.write(f"SUMMARY:  [{article['importance']}] {article['summary']}\n")
            if article["text"]:
                out.write(f"WORDS:    {len(article['text'].split())}\n\n{article['text']}\n")
            else:
                out.write("TEXT:     (not fetched)\n")
            out.write("\n" + "=" * 80 + "\n\n")
    print("Wrote", OUTPUT_FILE)
