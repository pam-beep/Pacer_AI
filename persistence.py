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
        return [], []
    try:
        with open(DATA_FILE, "r") as f:
            data_dict = json.load(f)
            # Support legacy format (list of projects) or new format (dict with projects and deleted)
            if isinstance(data_dict, list):
                projects = data_dict
                deleted = []
            else:
                projects = data_dict.get('projects', [])
                deleted = data_dict.get('deleted', [])

            for p in projects + deleted:
                if 'start_date' in p and isinstance(p['start_date'], str):
                    p['start_date'] = datetime.fromisoformat(p['start_date'])
                if 'end_date' in p and isinstance(p['end_date'], str):
                    p['end_date'] = datetime.fromisoformat(p['end_date'])
                if 'created_at' in p and isinstance(p['created_at'], str):
                    p['created_at'] = datetime.fromisoformat(p['created_at'])
                if 'deleted_at' in p and isinstance(p['deleted_at'], str):
                    p['deleted_at'] = datetime.fromisoformat(p['deleted_at'])
            return projects, deleted
    except (json.JSONDecodeError, ValueError):
        return [], []

def save_data(projects, deleted=None):
    if deleted is None: deleted = []
    with open(DATA_FILE, "w") as f:
        json.dump({"projects": projects, "deleted": deleted}, f, default=datetime_serializer, indent=4)

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

# --- Focus Timer Persistence ---
FOCUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pacer_focus.json")

def load_focus_data():
    if not os.path.exists(FOCUS_FILE):
        return []
    try:
        with open(FOCUS_FILE, "r") as f:
            data = json.load(f)
            for entry in data:
                if 'date' in entry and isinstance(entry['date'], str):
                    try:
                        entry['date'] = datetime.fromisoformat(entry['date'])
                    except:
                        # Fallback for other formats
                        try:
                            entry['date'] = datetime.strptime(entry['date'], "%Y-%m-%d %H:%M:%S")
                        except: pass
            # Sort by date
            data.sort(key=lambda x: x['date'] if isinstance(x['date'], datetime) else datetime.min)
            return data
    except (json.JSONDecodeError, ValueError):
        return []

def save_focus_data(sessions):
    with open(FOCUS_FILE, "w") as f:
        json.dump(sessions, f, default=datetime_serializer, indent=4)

# --- Tag Persistence ---
TAGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pacer_tags.json")

def load_tags():
    if not os.path.exists(TAGS_FILE):
        return ["Work", "Personal", "Urgent", "Health", "Social", "Learning"] # Defaults
    try:
        with open(TAGS_FILE, "r") as f:
            return json.load(f)
    except:
        return ["Work", "Personal", "Urgent", "Health", "Social", "Learning"]

def save_tags(tags):
    with open(TAGS_FILE, "w") as f:
        json.dump(tags, f, indent=4)
