import os 
import psycopg 

def get_db_connection():
    """
    Returns a psycopg connection.
        - On Railway (production): uses DATABASE_URL, which Railway auto-provides
        and injects once referenced in the app service's Variables tab.
        - Locally (development): falls back to a plain dbname=<DB_NAME> connection,
        since local Postgres needs no auth on your machine.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg.connect(database_url)
    else:
        db_name = os.getenv("DB_NAME", "bellie")
        return psycopg.connect(f"dbname={db_name}")