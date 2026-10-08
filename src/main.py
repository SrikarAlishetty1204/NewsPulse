import ctypes
import os
import sys
from datetime import date

import psutil
from dotenv import load_dotenv

from src.database import get_saved_urls, save_articles
from src.logger import LOG_DIR, logger
from src.mail_service import send_digest
from src.news_service import fetch_news

load_dotenv()

MIN_FREE_RAM_GB = float(os.getenv("MIN_FREE_RAM_GB", "8"))
# Holds the date of the last successful run
LAST_RUN_FILE = os.path.join(LOG_DIR, "last_run.txt")

if __name__ == "__main__":
    # The scheduled task starts every 30 minutes; only the first successful start each day does the work
    today = date.today().isoformat()
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE) as last_run:
            if last_run.read().strip() == today:
                logger.debug("already ran today, nothing to do")
                sys.exit(0)

    # The model loads into RAM; with too little free, Windows swaps and the PC crawls
    free_ram_gb = psutil.virtual_memory().available / 1024 ** 3
    if free_ram_gb < MIN_FREE_RAM_GB:
        logger.warning(f"only {free_ram_gb:.1f} GB RAM free, need {MIN_FREE_RAM_GB:g} GB; skipping until the next try")
        sys.exit(1)

    # Keep Windows awake until this process exits; a timer wake otherwise sleeps again after ~2 minutes
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

    try:
        # Saved URLs go in first so fetch_news skips them before any model call
        saved_urls = get_saved_urls()
        articles = fetch_news(saved_urls)
        # Usually the network isn't back yet after waking from sleep
        if not articles:
            logger.warning("no new entries in any feed; trying again at the next start")
            sys.exit(1)
        save_articles(articles)
        send_digest(articles)
    except Exception:
        logger.exception("run failed")
        sys.exit(1)

    with open(LAST_RUN_FILE, "w") as last_run:
        last_run.write(today)
    logger.info("run finished")
