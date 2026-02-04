import streamlit as st
import pandas as pd
import sys
import os
# Ensure local modules are found (Prepend to path)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from datetime import datetime, timedelta, date
from streamlit_calendar import calendar
from datetime import datetime, timedelta, date
from streamlit_calendar import calendar
from utils import generate_checklist
import uuid
import json
from review import render_review_dashboard
from persistence import load_data, save_data

# --- Config & Style ---
# ... (rest of file)


# --- Config & Style ---
st.set_page_config(page_title="Life OS · Pacer 3.4", layout="wide", page_icon="🌑")

# Requirements: High Contrast, Flat List, Date-Based Status
st.markdown("""
<style>
    /* Global Dark Mode */
    .stApp, .stApp > div, .stApp > header {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }
    
    /* Emergency Requirement: Fixed Calendar Scroll */
    
    /* 1. Fixed Container Height */
    .fc { 
        height: 700px !important; 
        background-color: #0E1117; /* Match Theme */
    }
    
    /* 2. Professional Scrollbar with Dedicated Lane */
    /* NO OVERLAP: padding-right ensures content doesn't touch the scrollbar */
    .fc-scroller {
        overflow-y: auto !important;
        padding-right: 20px !important; 
        scrollbar-width: thin;
        scrollbar-color: #444 #1A1C24;
    }
    
    /* Webkit Scrollbar Styling */
    .fc-scroller::-webkit-scrollbar {
        width: 14px !important; /* Visible width */
        background: #1A1C24 !important; /* Track background */
        display: block !important;
    }
    .fc-scroller::-webkit-scrollbar-thumb {
        background-color: #555 !important; /* High contrast thumb */
        border-radius: 7px !important;
        border: 3px solid #1A1C24 !important; /* Creates visual gap */
    }
    
    /* Clean up global scrollbar to avoid double bars */
    ::-webkit-scrollbar {
        width: 8px;
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: #333;
        border-radius: 4px;
    }
    
    /* Ensure content fits nicely */
    .main .block-container {
        padding-top: 1rem !important;
        padding-right: 1rem !important;
        padding-left: 1rem !important;
        max-width: 100% !important;
        padding-bottom: 0rem !important;
    }

    /* FIX: Light Mode Compatible Inputs */
    input, .stTextInput > div > div > input, textarea {
        color: #333333 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
    }
    input::placeholder, textarea::placeholder {
        color: #888888 !important;
        opacity: 1 !important;
    }
    
    /* FIX: Light Mode Compatible Buttons */
    .stButton > button {
        background-color: #00CC96 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover {
        background-color: #00AA7D !important;
        color: #FFFFFF !important;
    }
    
    /* Stats */
    .stat-card {
        background: #1A1C24;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stat-num { font-size: 1.5em; font-weight: bold; }
    .stat-lbl { font-size: 0.85em; color: #BBB; margin-top: 4px; }
    
    /* Calendar */
    .fc-event { 
        cursor: pointer; 
        border: none !important; 
        border-radius: 4px;
        font-size: 0.85em;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .fc-event:hover { filter: brightness(1.1); transform: translateY(-1px); transition: transform 0.1s; }
    
    /* Project Card */
    .project-card {
        background: #1A1C24;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 5px solid #555; /* Default */
        transition: all 0.2s;
    }
    .project-card:hover {
        background: #20222B;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        margin-left: 10px;
        font-weight: bold;
    }
    
    /* Utilities */
    .finished-text { text-decoration: line-through; color: #666; }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if 'projects' not in st.session_state:
    st.session_state.projects = load_data()
if 'selected_project_id' not in st.session_state:
    st.session_state.selected_project_id = None
if 'clicked_date' not in st.session_state:
    st.session_state.clicked_date = None
# For input clearing
if 'new_goal_input' not in st.session_state:
    st.session_state.new_goal_input = ""

def atomic_save():
    save_data(st.session_state.projects)

def calculate_completion(tasks):
    if not tasks: return 0.0
    completed = sum(1 for t in tasks if t['completed'])
    return completed / len(tasks)

def get_project_status(project):
    """
    Determine status based on Date and Progress.
    Today = System Time (e.g., 2026-02-02)
    1. 100% Done -> Completed
    2. Start > Today -> Not Started (Future)
    3. Start <= Today -> Active (In Progress)
    """
    pct = calculate_completion(project['tasks'])
    if pct >= 1.0:
        return "Completed", "#6E7280" # Gray
    
    today = datetime.now().date()
    # Ensure start_date is date object
    s_date = project['start_date'].date() if isinstance(project['start_date'], datetime) else project['start_date']
    
    if s_date > today:
        return "Not Started", "#EF553B" # Red/Orange (Future)
    else:
        return "Active", "#00CC96" # Green (Started/In Progress)

# --- Project Detail Dialog (Popup instead of Drawer) ---
@st.dialog("Project Details")
def show_project_dialog(proj_id):
    proj = next((p for p in st.session_state.projects if str(p['id']) == str(proj_id)), None)
    if not proj:
        st.error("Project not found.")
        return
    
    status, col = get_project_status(proj)
    
    # Header
    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        new_title = st.text_input("Goal", value=proj['goal'], key=f"dlg_title_{proj_id}")
        if new_title != proj['goal']:
            proj['goal'] = new_title
            atomic_save()
            st.rerun()
    with c2:
        st.markdown(f"<span style='color:{col}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)
    
    # Dates
    c_d1, c_d2 = st.columns(2)
    with c_d1:
        curr_start = proj['start_date'].date() if isinstance(proj['start_date'], datetime) else proj['start_date']
        new_s = st.date_input("Start Date", value=curr_start, key=f"dlg_start_{proj_id}")
        if new_s != curr_start:
            proj['start_date'] = datetime.combine(new_s, datetime.min.time())
            atomic_save()
            st.rerun()
    with c_d2:
        curr_end = proj['end_date'].date() if isinstance(proj['end_date'], datetime) else proj['end_date']
        new_e = st.date_input("End Date", value=curr_end, key=f"dlg_end_{proj_id}")
        if new_e != curr_end:
            proj['end_date'] = datetime.combine(new_e, datetime.min.time())
            atomic_save()
            st.rerun()
    
    # Progress Bars
    pct_exec = calculate_completion(proj['tasks'])
    start_d = proj['start_date'].date() if isinstance(proj['start_date'], datetime) else proj['start_date']
    end_d = proj['end_date'].date() if isinstance(proj['end_date'], datetime) else proj['end_date']
    today_d = datetime.now().date()
    total_days = (end_d - start_d).days + 1
    remaining_days = (end_d - today_d).days + 1
    if today_d < start_d: remaining_days = total_days
    elif today_d > end_d: remaining_days = 0
    pct_remaining = max(0.0, min(1.0, remaining_days / total_days if total_days > 0 else 0))
    
    st.caption(f"**Time Remaining**: {int(pct_remaining*100)}% ({remaining_days} days left)")
    st.progress(pct_remaining)
    st.caption(f"**Execution**: {int(pct_exec*100)}%")
    st.progress(pct_exec)
    
    st.divider()
    st.subheader("Checkpoints")
    
    # Migration
    for t in proj['tasks']:
        if 'id' not in t: t['id'] = str(uuid.uuid4())
    atomic_save()
    
    for i, t in enumerate(proj['tasks']):
        col_a, col_b, col_c = st.columns([0.05, 0.85, 0.1])
        with col_a:
            is_checked = st.checkbox("", value=t['completed'], key=f"dlg_chk_{t['id']}")
            if is_checked != t['completed']:
                t['completed'] = is_checked
                atomic_save()
                st.rerun()
        with col_b:
            task_name = t.get('task', t.get('name', 'Unnamed'))
            if t['completed']:
                st.write(f"~~{task_name}~~")
            else:
                st.write(task_name)
        with col_c:
            if st.button("x", key=f"dlg_del_t_{t['id']}"):
                proj['tasks'].pop(i)
                atomic_save()
                st.rerun()
    
    # Add Task
    new_task = st.text_input("Add Checkpoint", placeholder="New task...", key=f"dlg_new_t_{proj_id}")
    if st.button("Add", key=f"dlg_add_t_{proj_id}") and new_task:
        proj['tasks'].append({"id": str(uuid.uuid4()), "task": new_task, "completed": False})
        atomic_save()
        st.rerun()
    
    st.divider()
    if st.button("🗑️ Delete Project", key=f"dlg_del_proj_{proj_id}", type="primary"):
        st.session_state.projects = [p for p in st.session_state.projects if str(p['id']) != str(proj_id)]
        st.session_state.selected_project_id = None
        atomic_save()
        st.rerun()

# --- Logic: Add Project Callback ---
def add_project_callback():
    txt = st.session_state.new_goal_input
    if not txt.strip(): return
    
    # Pre-pend date if clicked (Calendar Click)
    full_txt = txt
    if st.session_state.clicked_date:
        full_txt += f" from {st.session_state.clicked_date.strftime('%Y-%m-%d')}"
    
    tasks, s_d, e_d = generate_checklist(full_txt)
    
    # Feature: Override with Sidebar Picker
    # Check if user selected dates in the sidebar picker
    if "sb_date_range" in st.session_state and st.session_state.sb_date_range:
        dates = st.session_state.sb_date_range
        if len(dates) > 0:
            # Override Start Date
            s_d = datetime.combine(dates[0], datetime.min.time())
            # Override End Date (if range selected, otherwise same as start)
            if len(dates) > 1:
                e_d = datetime.combine(dates[1], datetime.min.time())
            else:
                e_d = s_d

    new_id = str(uuid.uuid4())
    new_proj = {
        "id": new_id,
        "goal": txt, # Keep original text
        "tasks": tasks,
        "start_date": s_d,
        "end_date": e_d,
        "created_at": datetime.now()
    }
    st.session_state.projects.append(new_proj)
    atomic_save()
    
    # Clear inputs
    st.session_state.new_goal_input = ""
    st.session_state.clicked_date = None
    # Reset date picker
    st.session_state.sb_date_range = []

# --- Sidebar ---
with st.sidebar:
    st.header("Pacer 3.4")
    
    # 1. Stats based on Dynamic Status
    total = len(st.session_state.projects)
    cnt_completed = 0
    cnt_active = 0
    cnt_future = 0
    
    for p in st.session_state.projects:
        status, _ = get_project_status(p)
        if status == "Completed": cnt_completed += 1
        elif status == "Active": cnt_active += 1
        elif status == "Not Started": cnt_future += 1
        
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">
        <div class="stat-card"><div class="stat-num" style="color:#FFF;">{total}</div><div class="stat-lbl">Total</div></div>
        <div class="stat-card"><div class="stat-num" style="color:#6E7280;">{cnt_completed}</div><div class="stat-lbl">Finished</div></div>
        <div class="stat-card"><div class="stat-num" style="color:#00CC96;">{cnt_active}</div><div class="stat-lbl">Active</div></div>
        <div class="stat-card"><div class="stat-num" style="color:#EF553B;">{cnt_future}</div><div class="stat-lbl">Future</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # 2. Input Section
    lbl = "New Project"
    if st.session_state.clicked_date:
        lbl = f"New Project ({len(st.session_state.projects)} active)"
    
    # Formatting: Add User Guidance
    st.caption("Select dates first, then enter project info, or type dates and info directly in the input box.")
    
    # Feature: Sidebar Date Picker (Moved to Top)
    st.date_input(
        "Select Dates (Optional)", 
        value=[], 
        key="sb_date_range", 
        help="Select a range to override any dates in the text.",
        format="MM/DD/YYYY"
    )
    
    st.text_input(
        lbl, 
        key="new_goal_input", 
        placeholder="e.g. 2/8-2/20 Travel", 
        on_change=add_project_callback
    )
    
    st.caption("Press Enter in the text box to add.")
    
    if st.session_state.clicked_date:
        if st.button("Clear Date Selection"):
            st.session_state.clicked_date = None
            st.rerun()

# --- Main Layout ---
col_t, _ = st.columns([0.3, 0.7])
with col_t:
    view_mode = st.radio("View", ["Calendar", "Review"], horizontal=True, label_visibility="collapsed")

# 1. CALENDAR
if view_mode == "Calendar":
    events = []
    # ... (Keep existing Calendar Logic) ...
    for p in st.session_state.projects:
        status, color = get_project_status(p)
        vis_end = (p['end_date'] + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) \
                  if isinstance(p['end_date'], datetime) else p['end_date'] + timedelta(days=1)
        
        title = p['goal']
        if status == "Completed": title = f"✔ {title}"
        if status == "Not Started": title = f"⏳ {title}"
        
        s_str = p['start_date'].strftime('%Y-%m-%d')
        e_str = vis_end.strftime('%Y-%m-%d')
        
        events.append({
            "title": title,
            "start": s_str,
            "end": e_str,
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {"projectId": p['id']},
            "allDay": True
        })
        
    # Feature: Real-time Preview of Sidebar Selection
    if "sb_date_range" in st.session_state and st.session_state.sb_date_range:
        dates = st.session_state.sb_date_range
        if len(dates) > 0:
            draft_s = dates[0]
            draft_e = dates[1] if len(dates) > 1 else dates[0]
            d_vis_end = draft_e + timedelta(days=1)
            draft_title = st.session_state.new_goal_input if st.session_state.new_goal_input else "New Project..."
            
            events.append({
                "title": f"✨ {draft_title}",
                "start": draft_s.strftime('%Y-%m-%d'),
                "end": d_vis_end.strftime('%Y-%m-%d'),
                "backgroundColor": "#FFC107",
                "borderColor": "#FFC107",
                "textColor": "#000000",
                "display": "block",
                "opacity": 0.8,
                "allDay": True
            })
        
    opts = {
        "headerToolbar": {"left": "prev,next title", "center": "", "right": ""},
        "initialView": "dayGridMonth",
        "selectable": True,
        "editable": False,
        "timeZone": "local",
        "height": "700px"
    }
    
    st.subheader("Schedule")
    cal = calendar(events=events, options=opts, key="cal_main")
    
    if cal.get("eventClick"):
        cid = cal["eventClick"]["event"]["extendedProps"]["projectId"]
        if st.session_state.selected_project_id != cid:
            st.session_state.selected_project_id = cid
            st.rerun()
            
    if cal.get("dateClick"):
        dstr = cal["dateClick"]["date"]
        try:
            val = datetime.strptime(dstr, "%Y-%m-%d")
            if st.session_state.clicked_date != val:
                st.session_state.clicked_date = val
                st.rerun()
        except: pass

# 3. REVIEW DASHBOARD (Replaces List)
elif view_mode == "Review":
    # Clear Calendar selection when in Review to avoid linkage
    st.session_state.selected_project_id = None
    render_review_dashboard(st.session_state.projects)

# --- POPUP (Manage Project) - ONLY in Calendar View ---
if view_mode == "Calendar" and st.session_state.selected_project_id:
    show_project_dialog(st.session_state.selected_project_id)

