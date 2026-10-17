"""
Ingestion script. Parse journal entries, generate embeddings, and store them in PostgreSQL.
"""
import os 
from dotenv import load_dotenv
from openai import OpenAI
import psycopg
from db import get_db_connection
from parser import Entry, parse_journal
from pgvector.psycopg import register_vector

# Load OPENAI_API_KEY from .env into the environment
load_dotenv()
client = OpenAI()

# Turn one piece of text into a 1536-number embedding vector by calling the OpenAI embeddings API
def embed(text: str) -> list[float]: 
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding

# Parse journal and insert entries into bellie database
def main(): 
    # get journal file path and db name 
    journal_file = os.getenv("JOURNAL_FILE", "journal.txt")
    db_name = os.getenv("DB_NAME", "bellie")

    # read and parse journal export into a list of Entry objects
    with open(journal_file) as f:
        raw_text = f.read()
    entries: list[Entry] = parse_journal(raw_text)

    print(f"Parsed {len(entries)} entries. Connecting to database...")

    # connect to db 
    with get_db_connection() as conn:
        # tell python how to translate between python list and pgvector format
        register_vector(conn)

        # Guard: refuse to run if the table isn't empty, to avoid silently
        # creating duplicate rows on an accidental second run.
        if has_existing_entries(conn):
            print(f"'{db_name}' already has entries. Aborting to avoid duplicates.")
            print("Run `TRUNCATE TABLE entries;` in psql first if you want to re-ingest.")
            return

        with conn.cursor() as cur: 
            for i, entry in enumerate(entries): 
                # create an embedding vector for this entry's text by calling the OpenAI embeddings API
                vector = embed(entry.text)

                # insert the entry into the database with its embedding vector
                # (pass as a tuple to the execute method to avoid SQL injection attacks)
                cur.execute(
                    """
                    INSERT INTO entries (entry_date, content, embedding)
                    VALUES (%s, %s, %s)
                    """, 
                    (entry.date, entry.text, vector),
                )

                print(f"[{i+1}/{len(entries)}] Inserted entry from {entry.date}")

        # save all changes to the database
        conn.commit()

    print("Done")


# Returns True if the entries table already has rows.
# Used to guard against accidentally re-running ingestion and creating duplicates.
def has_existing_entries(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM entries")
        count = cur.fetchone()[0]
    return count > 0


if __name__ == "__main__":
    main()
                