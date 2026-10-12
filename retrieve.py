"""
Retrieve entries from the database most similar to a given question using embedding vectors.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
from pgvector import Vector
import psycopg
from pgvector.psycopg import register_vector
from datetime import date

load_dotenv()
client = OpenAI()

# convert question into embedding vector
# need to use the same model (vectors from diff models are not compatible)
def embed(text: str) -> list[float]:
    resp = client.embeddings.create(model=os.getenv("EMBEDDING_MODEL"), input=text)
    return resp.data[0].embedding


# retrieve entries most similar in meaning to the question by comparing embedding vectors
# start and end date are optional 
def retrieve(question: str, top_k: int = 5, start_date: str = None, end_date: str = None):

    question_vector = Vector(embed(question)) # convert the question into an embedding vector and cast into pgvector Vector object

    with psycopg.connect("dbname=" + os.getenv("DB_NAME")) as conn:
        register_vector(conn) # translate python list to pgvector format

        with conn.cursor() as cur:
            # base query: order all rows by vector distance to the question vector, limit to top_k. 
            # <=> computes cosine/euclidean distance between two vectors in pgvector. smaller distance = more similar.
            query = """
                SELECT entry_date, content, embedding <=> %(qvec)s AS distance
                FROM entries
            """
            params = {"qvec": question_vector, "top_k": top_k}

            # date filter 
            if start_date and end_date:
                start_date = date.fromisoformat(start_date)
                end_date = date.fromisoformat(end_date)

                query += " WHERE entry_date BETWEEN %(start)s AND %(end)s"
                params["start"] = start_date
                params["end"] = end_date

            query += " ORDER BY distance ASC LIMIT %(top_k)s"

            cur.execute(query, params)
            return cur.fetchall() # list of (entry_date, content, distance) tuples

# test only 
# python3 retrieve.py
if __name__ == "__main__":
    from datetime import date

    question = "How have I been feeling about my career?"
    results = retrieve(question, 5)    

    print(f"Question: {question}\n")
    for entry_date, content, distance in results: 
        print(f"{entry_date} - {content[:50]}... (distance: {distance:.4f})")

    print("\n--- Filtered to March 2026 only ---")
    march_results = retrieve(question, 5, start_date="2026-03-01", end_date="2026-03-31")
    for entry_date, content, distance in march_results:
        print(f"{entry_date} - {content[:50]}... (distance: {distance:.4f})")