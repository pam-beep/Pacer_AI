import os
import json
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pacer_store.json")

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            for p in data:
                # Handle ISO format parsing
                if 'start_date' in p and isinstance(p['start_date'], str):
                    p['start_date'] = datetime.fromisoformat(p['start_date'])
                if 'end_date' in p and isinstance(p['end_date'], str):
                    p['end_date'] = datetime.fromisoformat(p['end_date'])
                if 'created_at' in p and isinstance(p['created_at'], str):
                    p['created_at'] = datetime.fromisoformat(p['created_at'])
            return data
    except (json.JSONDecodeError, ValueError):
        return []


def save_data(projects):
    with open(DATA_FILE, "w") as f:
        json.dump(projects, f, default=datetime_serializer, indent=4)

# --- Journal Persistence ---
JOURNAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pacer_journal.json")

def load_journal():
    if not os.path.exists(JOURNAL_FILE):
        return []
    try:
        with open(JOURNAL_FILE, "r") as f:
            data = json.load(f)
            # Ensure dates are parsed
            for entry in data:
                if 'date' in entry and isinstance(entry['date'], str):
                    try:
                        # Try full datetime first, then date
                        entry['date'] = datetime.fromisoformat(entry['date'])
                    except:
                        pass
            # Sort by date descending
            data.sort(key=lambda x: x['date'] if isinstance(x['date'], datetime) else datetime.min, reverse=True)
            return data
    except (json.JSONDecodeError, ValueError):
        return []

def save_journal(entries):
    with open(JOURNAL_FILE, "w") as f:
        json.dump(entries, f, default=datetime_serializer, indent=4)
