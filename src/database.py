import os 
import pyodbc 
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_connection=yes;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(connection_string)


def get_saved_urls():
    """Every Url already in NewsArticles, so fetch_news can skip them."""
    connection = get_connection()
    saved_urls = set()
    for (url,) in connection.cursor().execute("SELECT Url FROM NewsArticles").fetchall():
        saved_urls.add(url)
    connection.close()
    return saved_urls


def save_articles(articles):
    """Insert every article that has a summary; returns how many were inserted."""
    connection = get_connection()
    cursor = connection.cursor()
    category_ids = {}
    for category_id, name in cursor.execute("SELECT Id, Name FROM Categories").fetchall():
        category_ids[name] = category_id

    inserted = 0
    for article in articles:
        if not article["summary"]:
            continue
        # The same link can appear in two feeds within one run
        if cursor.execute("SELECT 1 FROM NewsArticles WHERE Url = ?", article["link"]).fetchone():
            continue
        cursor.execute(
            "INSERT INTO NewsArticles (News, Url, CategoryId, Importance) VALUES (?, ?, ?, ?)",
            article["summary"], article["link"], category_ids[article["category"]], article["importance"]
        )
        inserted += 1
    connection.commit()
    connection.close()

    print("inserted", inserted)
    return inserted
