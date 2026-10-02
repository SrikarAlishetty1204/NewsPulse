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
