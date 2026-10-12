# Bellie Project

## To run 
1. source .venv/bin/activate
2. uvicorn main:app --reload

### Ingesting journal into DB 
1. Create the journal file 
2. Create a separate database for the journal in postgres 
```
createdb bellie_demo
psql bellie_demo

CREATE EXTENSION vector;
CREATE TABLE entries (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536)
);

\q
```
3. Point ingest.py at the new file and new database. 
```
DB_NAME=bellie_demo python3 -c "
from parser import parse_journal
import ingest

with open('synthetic_journal.txt') as f:
    raw = f.read()

entries = parse_journal(raw, year=2026)
print(f'Parsed {len(entries)} synthetic entries')
"
```
4. Verify count 
psql bellie_demo
SELECT COUNT(*) FROM entries;

