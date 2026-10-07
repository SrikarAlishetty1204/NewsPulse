from src.database import get_saved_urls, save_articles
from src.news_service import fetch_news

if __name__ == "__main__":
    # Saved URLs go in first so fetch_news skips them before any model call
    saved_urls = get_saved_urls()
    articles = fetch_news(saved_urls)
    save_articles(articles)
