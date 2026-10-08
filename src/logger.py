import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
# Absolute so the scheduled task writes to the project no matter where it starts
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "newspulse.log")

# Own name so library loggers (httpx, urllib3) don't flood the output
logger = logging.getLogger("newspulse")
logger.propagate = False
formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")

os.makedirs(LOG_DIR, exist_ok=True)
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# pythonw.exe (used by the scheduled task) has no console, so sys.stdout is None there
if sys.stdout is not None:
    # The Hindu titles contain zero-width characters that crash the default Windows console
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# DEBUG=true shows everything; false shows only warnings and errors
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARNING)
