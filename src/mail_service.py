import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
MAIL_TO = os.getenv("MAIL_TO")


def send_digest(articles):
    """Mail every summarized article, grouped by category, most important first."""
    summarized = []
    for article in articles:
        if article["summary"]:
            summarized.append(article)
    if not summarized:
        print("no new articles, mail not sent")
        return

    summarized.sort(key=lambda article: article["importance"], reverse=True)
    by_category = {}
    for article in summarized:
        by_category.setdefault(article["category"], []).append(article)

    lines = []
    for category, category_articles in by_category.items():
        lines.append(f"===== {category.upper()} =====\n")
        for article in category_articles:
            lines.append(f"[{article['importance']}/10] {article['title']}")
            lines.append(article["summary"])
            lines.append(f"Read more: {article['link']}\n")

    message = EmailMessage()
    message["Subject"] = f"NewsPulse digest: {len(summarized)} articles"
    message["From"] = SMTP_USER
    message["To"] = MAIL_TO
    message.set_content("\n".join(lines))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)
    print("mailed", len(summarized), "articles to", MAIL_TO)
