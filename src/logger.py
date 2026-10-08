import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Own name so library loggers (httpx, urllib3) don't flood the output
logger = logging.getLogger("newspulse")

# The Hindu titles contain zero-width characters that crash the default Windows console
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S"))
logger.addHandler(handler)
logger.propagate = False

# DEBUG=true shows everything; false shows only warnings and errors
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARNING)
