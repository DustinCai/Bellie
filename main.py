"""
Bellie 

Journals should be parsed and ingested into the appropriate DB beforehand. 
Wires retrieve and generation. Handles auth, validation, rate limiting and error handling. 

Request flow for ask (POST): 
1. verify_api_key() checks the x-api-key header (auth gate)
2. AskRequest validates the JSON body (question length, real dates)
3. retrieve() embeds the question and finds similar journal entries in postgres
4. generate() sends those entries + question to Claude and gets an answer back 
5. response returns as json 

Run locally with:
    uvicorn main:app --reload
Then test interactively at http://127.0.0.1:8000/docs with swagger 

"""
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Header, Request
from fastapi.security import APIKeyHeader
from retrieve import retrieve
from generate import generate
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from fastapi.responses import JSONResponse

# tracks request count per client (by IP) and auto rejects with 429 response 
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI()


# -- Rate limiting setup -- 
# Initialize the rate limiter and register it with the FastAPI app
limiter = Limiter(key_func=get_remote_address) # initialize the rate limiter using the client's IP address as the key
app.state.limiter = limiter # register on fastapi app.state + exception handler lets FASTAPI auto return 429 when rate limit is exceeded
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) 

# -- Request validation -- 
# Request model for /ask endpoint (fastapi validates payload against this model)
class AskRequest(BaseModel):
    question: str = Field(..., min_length = 1, max_length = 200, description="The question to ask")
    start_date: date | None = None # optional start date for filtering entries
    end_date: date | None = None   # optional end date for filtering entries


# -- Authentication -- 
# Declares "x-api-key" as a recognized security scheme 
# This is what makes /docs show a proper Authorize button instead of a plain text field you re-type every time.
api_key_header = APIKeyHeader(name="x-api-key")

# Checks the request includes the correct API key in its headers. 
# secrets.compare_digest prevents a timing attack — a plain == comparison
# can leak info about the key by how long it takes to fail.
def verify_api_key(x_api_key: str = Depends(api_key_header)):
    """
    Checks the request's x-api-key header against BELLIE_API_KEY (app key)
    secrets.compare_digest (instead of ==) avoids timing attacks (a normal
    == comparison can leak info about how much of the key matched based on
    how long the comparison took)
    """
    expected_api_key = os.getenv("BELLIE_API_KEY")
    if not x_api_key or not secrets.compare_digest(x_api_key, expected_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized") # invalid or missing API key


# -- Global error handling --
# Catches any unhandled exception anywhere in the app and returns a generic
# message instead of leaking internal details to the caller.
@app.exception_handler(Exception) # registers a catch-all at the ASGI app level
async def generic_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled error on {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again."},
    )

# --- Routes --- 

@app.get("/health")
def health():
    return {"status": "ok"}


# Takes a question, retrieves relevant entries, and asks claude to answer based on the entries. 
# Note: 'request: Request' is required for slowapi to read caller's IP 
# `_=Depends(verify_api_key)` runs the auth check before function executes 
@app.post("/ask")
@limiter.limit("10 per minute") # limit the /ask endpoint to 10 requests per minute per IP 
def ask(request: Request, req: AskRequest, _=Depends(verify_api_key)): 

    # grab top_k most relevant entries
    entries = retrieve(
        req.question,
        top_k=7,
        start_date = str(req.start_date) if req.start_date else None,
        end_date = str(req.end_date) if req.end_date else None,
    ) 

    # generate answer with entries 
    answer = generate(req.question, entries)    

    return {"answer": answer}