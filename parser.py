"""
Parse journal entries into structured Entry objects for ingestion script. 
"""
import re 
from dataclasses import dataclass
from datetime import date 

# Parsed journal entry
@dataclass
class Entry:
    date: date
    text: str


# Regex that matches lines like "9/26 Saturday" at the start of a line.
# Captures the month and day as groups so we can build a real date from them.
DATE_HEADER = re.compile(r"^(\d{1,2})/(\d{1,2})\s+\w+\s*$", re.MULTILINE) 


'''
    Parse a raw journal text into a list of Entry objects.
    
    Args:
        raw_text (str): The raw text of the journal.
        year (int): The year to use for entries without an explicit year. Defaults to the current year.

    Returns:
        list[Entry]: A list of parsed journal entries.
'''
def parse_journal(raw_text: str, year: int = date.today().year) -> list[Entry]:
    # find every entry by date header and where it sits in the text
    matches = list(DATE_HEADER.finditer(raw_text))

    entries = [] 
    for i, match in enumerate(matches):
        # get month and day 
        month, day = int(match.group(1)), int(match.group(2)) 

        # entry text runs from end of this header to the start of the next header
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        body = raw_text[start:end].strip()

        # create an Entry object for this date and body and add it to the list
        entries.append(Entry(date=date(year, month, day), text=body))

    return entries


# Only runs when you execute this script directly. Won't run if this file is imported as a module.
if __name__ == "__main__":
    with open("sample_journal.txt") as f:
        raw_text = f.read()

    entries = parse_journal(raw_text)

    for entry in entries:
        #print(f"{entry.date}: {entry.text}")
        print(entry.date, "-", entry.text[:50], "...")