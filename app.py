import streamlit as st

import pandas as pd
import sys
import os
# Ensure local modules are found (Prepend to path)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from streamlit_calendar import calendar
from utils import generate_checklist, extract_tags
import uuid
import json
import textwrap # For safe HTML dedenting
from review import render_review_dashboard
from persistence import load_data, save_data
from styles import GLOBAL_STYLES

# --- Config & Style ---
# ... (rest of file)


# --- Config & Style ---
st.set_page_config(page_title="Life OS · Pacer 3.4", layout="wide", page_icon="🌑")

# Requirements: High Contrast, Flat List, Date-Based Status
st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

# --- Session State ---
if 'projects' not in st.session_state:
    st.session_state.projects = load_data()
if 'tags' not in st.session_state:
    # Initialize basic tags
    st.session_state.tags = ["Work", "Personal", "Urgent", "Health", "Social", "Learning"]
if 'new_project_tags' not in st.session_state:
    st.session_state.new_project_tags = []
if 'calendar_version' not in st.session_state:
    st.session_state.calendar_version = 0
if 'ignore_calendar_click' not in st.session_state:
    st.session_state.ignore_calendar_click = False
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

# --- Day 2: Rhythm Score ---
def calculate_rhythm_score(projects):
    """
    Calculate rhythm score (0-100) based on on-time completion rate.
    On-time = project completed (100%) before or on end_date.
    """
    completed_projects = [p for p in projects if calculate_completion(p['tasks']) >= 1.0]
    if not completed_projects:
        return 100  # No completed projects = perfect rhythm (no failures)
    
    on_time_count = 0
    for p in completed_projects:
        end_d = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
        # Use completed_at as proxy for completion date if available
        completed_d = p.get('completed_at')
        if completed_d:
            # Handle string, datetime, or date types
            if isinstance(completed_d, str):
                try:
                    check_d = datetime.fromisoformat(completed_d).date()
                except:
                    check_d = datetime.now().date()
            elif isinstance(completed_d, datetime):
                check_d = completed_d.date()
            else:
                check_d = completed_d  # Already a date
        else:
            check_d = datetime.now().date()  # Fallback
        
        if check_d <= end_d:
            on_time_count += 1
    
    return int((on_time_count / len(completed_projects)) * 100)

# --- Global Resources ---
res_bin_path = "/Users/pampan/.gemini/antigravity/brain/4499dd3b-5597-468b-8851-f1d47790ac74/pixel_art_recycle_bin_transparent_1770466742660.png"

import base64
def get_image_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""


# --- Day 2: Time Debt ---
def calculate_time_debt(projects):
    """
    Calculate total time debt/credit in days.
    Debt = late completion (negative)
    Credit = early completion (positive)
    """
    completed_projects = [p for p in projects if calculate_completion(p['tasks']) >= 1.0]
    if not completed_projects:
        return 0
    
    total_delta = 0
    for p in completed_projects:
        start_d = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
        end_d = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
        planned_days = (end_d - start_d).days + 1
        
        # Use completed_at if available, else assume completed today
        completed_d = p.get('completed_at')
        if completed_d:
            # Handle string, datetime, or date types
            if isinstance(completed_d, str):
                try:
                    check_d = datetime.fromisoformat(completed_d).date()
                except:
                    check_d = datetime.now().date()
            elif isinstance(completed_d, datetime):
                check_d = completed_d.date()
            else:
                check_d = completed_d  # Already a date
        else:
            check_d = datetime.now().date()
        
        actual_days = (check_d - start_d).days + 1
        delta = planned_days - actual_days  # Positive = early, Negative = late
        total_delta += delta
    
    return total_delta

# --- New Project Dialog (For Drafts) ---
@st.dialog("Create New Project")
def show_new_project_dialog():
    # Defaults from Sidebar or Previous Input
    goal_val = st.session_state.new_goal_input if st.session_state.new_goal_input else ""
    
    start_val = datetime.now()
    end_val = datetime.now() + timedelta(days=7)
    
    if "sb_date_range" in st.session_state and st.session_state.sb_date_range:
        dates = st.session_state.sb_date_range
        if len(dates) > 0:
            start_val = datetime.combine(dates[0], datetime.min.time())
            if len(dates) > 1:
                end_val = datetime.combine(dates[1], datetime.min.time())
            else:
                end_val = start_val
    
    st.caption("Confirm details for your new project.")
    
    new_goal = st.text_input("Project Goal", value=goal_val, placeholder="e.g. Learn Python")
    
    c1, c2 = st.columns(2)
    with c1:
        new_s = st.date_input("Start Date", value=start_val)
    with c2:
        new_e = st.date_input("End Date", value=end_val)
        
    # Tags Selection
    # Use session state from Sidebar if available
    def_tags = st.session_state.get('new_project_tags', [])
    # Filter to ensure valid
    def_tags = [t for t in def_tags if t in st.session_state.tags]
    
    sel_tags = st.multiselect("Tags", options=st.session_state.tags, default=def_tags, key="dlg_new_tags")
        
    st.divider()
    
    b1, b2 = st.columns([1, 1])
    with b1:
        if st.button("Create Project", type="primary", use_container_width=True):
            if new_goal.strip():
                # Use helper to create
                create_project(new_goal, 
                               datetime.combine(new_s, datetime.min.time()), 
                               datetime.combine(new_e, datetime.min.time()),
                               tags=sel_tags)
                
                # Clear sidebar selection / draft
                st.session_state.selected_project_id = None
                if "sb_date_range" in st.session_state:
                    del st.session_state.sb_date_range
                st.session_state.new_goal_input = ""
                # Force full rerun and reset calendar
                st.session_state.calendar_version += 1
                st.session_state.ignore_calendar_click = True
                st.rerun()
            else:
                st.error("Please enter a goal.")
                
    with b2:
        if st.button("Cancel / Delete Draft", use_container_width=True):
            # Clear sidebar selection / draft
            st.session_state.selected_project_id = None
            if "sb_date_range" in st.session_state:
                del st.session_state.sb_date_range
            st.session_state.new_goal_input = ""
            # Force full rerun and reset calendar
            st.session_state.calendar_version += 1
            st.session_state.ignore_calendar_click = True
            st.rerun()

# --- Project Detail Dialog (Popup instead of Drawer) ---
@st.dialog("Project Details")
def show_project_dialog(proj_id):
    proj_id = str(proj_id)
    if 'projects' not in st.session_state:
        st.error("Session data missing.")
        return
    
    # Locate Project
    proj = next((x for x in st.session_state.projects if str(x.get('id')) == proj_id), None)
    
    if not proj:
        st.error(f"Project not found. ID: {proj_id}")
        if st.button("Close"): st.rerun()
        return

    # Celebration Logic (Handled globally, but we can clear state here if needed)
    pass

    status, col = get_project_status(proj)
    
    # --- HEADER: Title & Status ---
    c1, c2 = st.columns([0.75, 0.25])
    with c1:
        new_title = st.text_input("Goal", value=proj['goal'], key=f"dlg_title_{proj_id}")
        if new_title != proj['goal']:
            proj['goal'] = new_title
            atomic_save()
            st.rerun()
    with c2:
        st.markdown(f'<div style="height: 28px;"></div>', unsafe_allow_html=True) # Spacer
        st.markdown(f"<div class='pixel-status-badge' style='color:{col}; border-color:{col};'>{status}</div>", unsafe_allow_html=True)
    
    # --- DATES ---
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
            
    # --- REWARD & TAGS ---
    curr_reward = proj.get('reward', '')
    new_reward = st.text_input("🎁 Reward", value=curr_reward, key=f"dlg_reward_{proj_id}", placeholder="Reward for yourself...")
    if new_reward != curr_reward:
        proj['reward'] = new_reward
        atomic_save()

    curr_tags = proj.get('tags', [])
    new_tags = st.multiselect("Tags", options=st.session_state.tags, default=[t for t in curr_tags if t in st.session_state.tags], key=f"dlg_tags_{proj_id}")
    if new_tags != curr_tags:
        proj['tags'] = new_tags
        atomic_save()
        st.rerun()

    # --- PROGRESS BAR (Pixel Style) ---
    pct_exec = calculate_completion(proj['tasks'])
    st.markdown(f"""
    <div style="margin-top: 10px; margin-bottom: 5px; font-family: 'VT323', monospace; color: #002FA7;">
        EXECUTION: {int(pct_exec*100)}%
    </div>
    <div style="width: 100%; height: 16px; background: #E0E0E0; border: 2px solid #002FA7; position: relative;">
        <div style="width: {int(pct_exec*100)}%; height: 100%; background: #00CC96; border-right: 2px solid #002FA7;"></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # --- CHECKPOINTS (Tasks) ---
    st.markdown("<div style='font-family: VT323; font-size: 20px; color: #002FA7; margin-bottom: 10px;'>CHECKPOINTS</div>", unsafe_allow_html=True)
    
    # Checkpoints
    for i, t in enumerate(proj['tasks']):
        col_a, col_b, col_c = st.columns([0.05, 0.85, 0.1])
        with col_a:
            is_checked = st.checkbox("", value=t['completed'], key=f"dlg_chk_{t.get('id', i)}")
            if is_checked != t['completed']:
                t['completed'] = is_checked
                atomic_save()
                # Check completion
                all_done = all(task['completed'] for task in proj['tasks'])
                if all_done and is_checked:
                    proj['completed_at'] = datetime.now()
                    atomic_save()
                    st.session_state.celebrate_project = proj_id
                st.rerun()
        with col_b:
            task_name = t.get('task', t.get('name', 'Unnamed'))
            if t['completed']:
                st.markdown(f"<span style='color: #6E7280; text-decoration: line-through; font-family: VT323; font-size: 18px;'>{task_name}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color: #002FA7; font-family: VT323; font-size: 18px;'>{task_name}</span>", unsafe_allow_html=True)
        with col_c:
            if st.button("x", key=f"dlg_del_t_{t.get('id', i)}", help="Remove Checkpoint"):
                proj['tasks'].pop(i)
                atomic_save()
                st.rerun()
    
    # Add Task
    new_task = st.text_input("New Checkpoint", placeholder="Type next step...", key=f"dlg_new_t_{proj_id}", label_visibility="collapsed")
    if st.button("ADD", key=f"dlg_add_t_{proj_id}", use_container_width=True) and new_task:
        proj['tasks'].append({"id": str(uuid.uuid4()), "task": new_task, "completed": False})
        atomic_save()
        st.rerun()
        
    st.markdown("---")
    
    # --- DELETE SECTION (Recycle Bin Icon) ---
    # Layout: [Icon] [Delete Button]
    c_del_ico, c_del_btn = st.columns([0.2, 0.8])
    
    with c_del_ico:
        # Render Recycle Bin Image (Base64)
        bin_b64 = get_image_base64(res_bin_path)
        if bin_b64:
             st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{bin_b64}" width="50"></div>', unsafe_allow_html=True)
        else:
             st.markdown("🗑️")

    with c_del_btn:
        st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True) # Vertical Spacer
        if st.button("THROW IN BIN", key=f"dlg_del_proj_{proj_id}", type="primary", use_container_width=True):
            # Soft Delete Logic
            if 'deleted_projects' not in st.session_state: st.session_state.deleted_projects = []
            proj_to_del = next((p for p in st.session_state.projects if str(p['id']) == str(proj_id)), None)
            if proj_to_del:
                proj_to_del['deleted_at'] = datetime.now().isoformat()
                st.session_state.deleted_projects.append(proj_to_del)
            
            st.session_state.projects = [p for p in st.session_state.projects if str(p['id']) != str(proj_id)]
            st.session_state.selected_project_id = None
            atomic_save()
            st.toast("Moved to Recycle Bin", icon="🗑️")
            st.rerun()

# --- Logic: Add Project Callback ---
# Helper: Create Project Logic (Reusable)
def create_project(goal, start_date=None, end_date=None, tasks=None, tags=None):
    if not goal.strip(): return
    
    # 1. Generate Info if needed
    final_tasks = tasks
    s_d = start_date
    e_d = end_date
    
    # If not provided, try to parse from text
    if not final_tasks:
        # Pre-pend date context if available (only if parsing from text)
        full_txt = goal
        if st.session_state.get('clicked_date') and not s_d:
             full_txt += f" from {st.session_state.clicked_date.strftime('%Y-%m-%d')}"
        
        generated_tasks, gen_s, gen_e = generate_checklist(full_txt)
        final_tasks = generated_tasks
        if not s_d: s_d = gen_s
        if not e_d: e_d = gen_e

    # 2. Ensure dates are set
    if not s_d: s_d = datetime.now()
    if not e_d: e_d = s_d + timedelta(days=7)

    new_id = str(uuid.uuid4())
    new_proj = {
        "id": new_id,
        "goal": goal,
        "tasks": final_tasks,
        "start_date": s_d,
        "end_date": e_d,
        "tags": tags if tags is not None else extract_tags(goal)[0], # Use provided tags, else extract from goal
        "created_at": datetime.now()
    }
    st.session_state.projects.append(new_proj)
    atomic_save()
    return new_id

# --- Logic: Add Project Callback ---
def add_project_callback():
    txt = st.session_state.new_goal_input
    if not txt.strip(): return
    
    # Check sidebar override
    s_d = None
    e_d = None
    
    if "sb_date_range" in st.session_state and st.session_state.sb_date_range:
        dates = st.session_state.sb_date_range
        if len(dates) > 0:
            s_d = datetime.combine(dates[0], datetime.min.time())
            if len(dates) > 1:
                e_d = datetime.combine(dates[1], datetime.min.time())
            else:
                e_d = s_d
    
    # Get tags from Sidebar multiselect
    # If using sidebar text input, we check the new_project_tags state
    # Get tags from Sidebar multiselect
    # Use widget key 'new_project_tags_selection' directly
    sb_tags = st.session_state.get('new_project_tags_selection', [])
    create_project(txt, s_d, e_d, tags=sb_tags)
    
    # Clear inputs
    st.session_state.new_goal_input = ""
    st.session_state.clicked_date = None
    # Reset date picker by deleting the key (avoids conflict with default value)
    if "sb_date_range" in st.session_state:
        del st.session_state.sb_date_range

# Defaults
if 'view_mode' not in st.session_state: st.session_state.view_mode = "Calendar"

# --- Sidebar ---
# --- Sidebar ---
with st.sidebar:
    # Reduce top padding of sidebar
    # --- Sidebar ---
    # Reduce top padding of sidebar
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
        
        /* GLOBAL PIXEL ART THEME override */
        .stApp, .stApp > header {
            font-family: 'VT323', monospace !important;
            letter-spacing: 0.5px;
            /* Ensure background is consistently Klein Blue */
            background-color: #002FA7 !important;
        }
        
        section[data-testid="stSidebar"] div.block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Pixel Art Sidebar Buttons (Vibrant Game Style) */
        section[data-testid="stSidebar"] div.stButton button,
        section[data-testid="stSidebar"] div.stDownloadButton button {
            height: 52px !important;
            width: 100% !important;
            white-space: nowrap !important;
            padding: 0 16px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 22px !important; /* Larger for pixel font */
            font-weight: bold !important;
            font-family: 'VT323', monospace !important;
            
            /* Pixel Art Style: Yellow Button, Blue Text */
            background-color: #F9DC24 !important; /* Schonbrunn Yellow */
            color: #002FA7 !important; /* Klein Blue */
            border: 4px solid #002FA7 !important;
            border-radius: 0px !important; /* No rounded corners */
            box-shadow: 6px 6px 0px 0px #000000 !important; /* Hard black shadow */
            transition: all 0.1s ease !important;
            text-transform: uppercase !important;
        }
        
        section[data-testid="stSidebar"] div.stButton button:hover,
        section[data-testid="stSidebar"] div.stDownloadButton button:hover {
            transform: translate(2px, 2px) !important;
            box-shadow: 4px 4px 0px 0px #000000 !important;
            background-color: #FFFFFF !important; /* White Hover */
            color: #002FA7 !important;
        }
        
        section[data-testid="stSidebar"] div.stButton button:active,
        section[data-testid="stSidebar"] div.stDownloadButton button:active {
            transform: translate(2px, 2px) !important;
            box-shadow: 2px 2px 0px #002FA7 !important;
        }

        /* Small Buttons in Grids (Tags, Add, Open Bin) */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button {
            height: auto !important;
            min-height: 0px !important;
            padding: 4px 8px !important;
            font-size: 16px !important;
            line-height: 1.2 !important;
            width: auto !important;
            display: inline-flex !important;
            margin-bottom: 4px !important;
        }
        
        section[data-testid="stSidebar"] div.stButton button:focus {
            box-shadow: 6px 6px 0px 0px #000000 !important;
            outline: none !important;
        }

        /* Digital Clock Style for Timer (Blue/Yellow Theme) */
        .digital-clock-container {
            background-color: #002FA7; /* Klein Blue */
            border: 4px solid #F9DC24; /* Yellow Border */
            border-radius: 0px;
            padding: 10px;
            text-align: center;
            box-shadow: 4px 4px 0px #000000;
            margin-bottom: 10px;
        }
        .digital-clock-display {
            font-family: 'VT323', monospace;
            font-size: 56px; /* Larger */
            color: #F9DC24; /* Yellow Text */
            text-shadow: 2px 2px 0px #000000;
            line-height: 1;
            letter-spacing: 4px;
            font-weight: bold;
        }
        .digital-clock-label {
             font-size: 14px;
             color: #F9DC24;
             opacity: 0.8;
             text-transform: uppercase;
             letter-spacing: 2px;
             margin-bottom: 4px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.header("Pacer 3.5")
    
    # --- NAVIGATION (Moved to Top) ---
    c_nav1, c_nav2 = st.columns([1, 1], gap="small")
    with c_nav1:
        if st.button("📅 Calendar", key="sb_nav_cal", type="primary" if st.session_state.view_mode == "Calendar" else "secondary", use_container_width=True):
            st.session_state.view_mode = "Calendar"
            st.rerun()
    with c_nav2:
        if st.button("📊 Review", key="sb_nav_rev", type="primary" if st.session_state.view_mode == "Review" else "secondary", use_container_width=True):
            st.session_state.view_mode = "Review"
            st.rerun()
            
    st.markdown("---")
    
    # --- 1. SEARCH ---
    search_query = st.text_input("Search", placeholder="🔍 Filter...", label_visibility="collapsed")
    
    # --- 2. BANK PASSBOOK ---
    rhythm = calculate_rhythm_score(st.session_state.projects)
    debt = calculate_time_debt(st.session_state.projects)
    
    # Dynamic Encouragement Logic
    if debt > 0:
        d_color = "#2E7D32"; d_label = f"+{debt} DAYS"; d_icon = "CREDIT"
        enc_text = "EXCELLENT PACE!"
        enc_color = "#2E7D32" # Green
    elif debt < -5:
        d_color = "#C62828"; d_label = f"{debt} DAYS"; d_icon = "DEBT"
        enc_text = "WARNING: CATCH UP!"
        enc_color = "#C62828" # Red
    elif debt < 0:
        d_color = "#C62828"; d_label = f"{debt} DAYS"; d_icon = "DEBT"
        enc_text = "PUSH HARDER!"
        enc_color = "#EF6C00" # Orange
    else:
        d_color = "#5D4037"; d_label = "BALANCED"; d_icon = "---"
        enc_text = "BALANCED FLOW"
        enc_color = "#5D4037" # Brown

    # Rhythm color
    if rhythm >= 80: r_color = "#2E7D32" 
    elif rhythm >= 50: r_color = "#EF6C00" 
    else: r_color = "#C62828"

    st.markdown(f'''
    <div class="passbook-container">
        <div class="passbook-inner-page">
            <div class="passbook-header">TIME BANK</div>
            <div class="passbook-row">
                <span class="passbook-label">RHYTHM SCORE</span>
                <span class="passbook-large-val">{rhythm}</span>
                <span style="font-size:12px; color:{r_color}; font-weight:bold;">PTS</span>
            </div>
            <div class="passbook-row">
                <span class="passbook-label">{d_icon}</span>
                <span class="passbook-large-val">{debt}</span>
                <span style="font-size:12px; color:{d_color}; font-weight:bold;">DAYS</span>
            </div>
            <div class="passbook-footer" style="color:{enc_color};">
                // {enc_text} //
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # --- 3. PROJECT STATS ---
    cnt_total = len(st.session_state.projects)
    cnt_completed = 0
    cnt_active = 0
    cnt_future = 0
    cnt_delayed = 0
    
    today = datetime.now().date()
    for p in st.session_state.projects:
        pct = calculate_completion(p['tasks'])
        if pct >= 1.0:
            cnt_completed += 1
            continue     
        start_d = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
        end_d = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
        remaining_days = (end_d - today).days + 1
        
        if today < start_d: cnt_future += 1
        elif remaining_days <= 0: cnt_delayed += 1
        else: cnt_active += 1

    # --- 3. PROJECT STATS ---
    with st.container(border=True):
        st.markdown('<div class="sidebar-module-title">PROJECT DASHBOARD</div>', unsafe_allow_html=True)
        # 2x2 Grid Layout
        st.markdown(f'''
        <div class="stat-grid">
            <div class="stat-box">
                <div class="stat-num" style="color:#B45309;">{cnt_active}</div>
                <div class="stat-label">ACTIVE</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="color:#1D4ED8;">{cnt_future}</div>
                <div class="stat-label">PLANNED</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="color:#B91C1C;">{cnt_delayed}</div>
                <div class="stat-label">DELAYED</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="color:#4B5563;">{cnt_completed}</div>
                <div class="stat-label">DONE</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # --- 4. FOCUS TIMER ---
    if 'focus_mode_active' not in st.session_state: st.session_state.focus_mode_active = False
    if 'focus_end_time' not in st.session_state: st.session_state.focus_end_time = datetime.now()
    if 'focus_duration' not in st.session_state: st.session_state.focus_duration = 25
    
    remaining_min = 0
    if st.session_state.focus_mode_active:
        now = datetime.now()
        if now < st.session_state.focus_end_time:
             diff = st.session_state.focus_end_time - now
             remaining_min = int(diff.total_seconds() // 60)
        else:
             st.session_state.focus_mode_active = False # Timer done
    else:
        remaining_min = st.session_state.focus_duration
    
    with st.container(border=True):
        st.markdown('<div class="sidebar-module-title">FOCUS TIMER</div>', unsafe_allow_html=True)
        
        # Digital Clock UI
        clock_status = "ACTIVE" if st.session_state.focus_mode_active else "READY"
        clock_color = "#F9DC24" if st.session_state.focus_mode_active else "#FFFFFF" # Yellow if active, White if not (Blue bg)
        
        # If active, calculate MM:SS
        display_time = f"{remaining_min:02d}:00"
        if st.session_state.focus_mode_active:
             diff = st.session_state.focus_end_time - datetime.now()
             t_sec = int(diff.total_seconds())
             if t_sec < 0: t_sec = 0
             mm = t_sec // 60
             ss = t_sec % 60
             display_time = f"{mm:02d}:{ss:02d}"
             
        # Render Clock
        st.markdown(f'''
        <div class="digital-clock-container">
            <div class="digital-clock-label">{clock_status}</div>
            <div class="digital-clock-display" style="color:{clock_color}; text-shadow: 2px 2px 0px #000;">
                {display_time}
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Controls inside container
        if st.session_state.focus_mode_active:
            if st.button("STOP", key="btn_stop_focus", type="primary", use_container_width=True):
                st.session_state.focus_mode_active = False
                st.rerun()
        else:
            f_dur = st.number_input("Duration (min)", 5, 120, st.session_state.focus_duration, step=5, label_visibility="collapsed")
            st.session_state.focus_duration = f_dur
            
            if st.button("START FOCUS", key="btn_start_focus", type="primary", use_container_width=True):
                 st.session_state.focus_mode_active = True
                 st.session_state.focus_end_time = datetime.now() + timedelta(minutes=st.session_state.focus_duration)
                 st.rerun()

    # --- 5. NEW PROJECT ---
    def on_sidebar_date_change():
        st.session_state.selected_project_id = None

    with st.container(border=True):
        st.markdown('<div class="sidebar-module-title">NEW MISSION</div>', unsafe_allow_html=True)
        
        st.caption("1. Select Dates")
        st.date_input(
            "Select Dates", value=[], key="sb_date_range", 
            format="MM/DD/YYYY", label_visibility="collapsed", on_change=on_sidebar_date_change
        )
        
        st.caption("2. Define Goal")
        st.text_input(
            "Goal", key="new_goal_input", placeholder="e.g. Run Marathon", label_visibility="collapsed"
        )
        
        st.caption("3. Assign Tags")
        sel_tags = st.multiselect(
            "Select Tags",
            options=st.session_state.tags,
            default=[],
            key="new_project_tags_selection",
            label_visibility="collapsed",
        )
        
        st.button("✨ Create Project", type="primary", use_container_width=True, on_click=add_project_callback)

    # --- 6. SETTINGS / TAGS ---
    with st.container(border=True):
         st.markdown('<div class="sidebar-module-title">SYSTEM SETTINGS</div>', unsafe_allow_html=True)
         
         # Flattened Tag Management
         c1, c2 = st.columns([0.7, 0.3])
         new_tag_txt = c1.text_input("New Tag", placeholder="New Tag Name", label_visibility="collapsed")
         if c2.button("Add", use_container_width=True):
             if new_tag_txt and new_tag_txt not in st.session_state.tags:
                 st.session_state.tags.append(new_tag_txt)
                 st.rerun()
         
         st.markdown("---")
         st.caption("Manage Tags (Scrollable):")
         
         # Scrollable Container for Tags
         with st.container(height=200):
             # COMPACT CSS for this section only
             st.markdown("""
                 <style>
                 /* Compact Text Input */
                 div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-baseweb="input"] {
                     height: 32px !important;
                     min-height: 32px !important;
                     padding: 0px 8px !important;
                 }
                 div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] input {
                     height: 32px !important;
                     min-height: 32px !important;
                     font-size: 16px !important;
                     padding: 0px !important;
                 }
                 /* Compact Delete Button */
                 div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] button {
                     height: 32px !important;
                     min-height: 32px !important;
                     padding: 0px !important;
                     font-size: 14px !important;
                     line-height: 1 !important;
                 }
                 /* Reduce Row Spacing */
                 div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] {
                     gap: 0.5rem !important; /* Smaller gap between columns */
                     margin-bottom: -10px !important; /* Bring rows closer */
                 }
                 /* Center Bullet */
                 div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stMarkdownContainer"] p {
                     margin-bottom: 0px !important;
                     line-height: 32px !important; /* Vertically center bullet */
                 }
                 </style>
             """, unsafe_allow_html=True)

             # List Layout (Bullet + Editable Text + Delete X)
             for i, t in enumerate(st.session_state.tags):
                 c_bull, c_val, c_del = st.columns([0.1, 0.7, 0.2])
                 
                 with c_bull:
                     st.markdown("<div style='text-align:center; font-size: 20px; line-height: 30px;'>•</div>", unsafe_allow_html=True)

                 # Editable Tag Name
                 new_val = c_val.text_input("Edit", value=t, key=f"edit_tag_{i}", label_visibility="collapsed")
                 if new_val != t:
                     if new_val and new_val not in st.session_state.tags:
                         st.session_state.tags[i] = new_val
                         # Update all projects with this tag
                         for p in st.session_state.projects:
                             if 'tags' in p and t in p['tags']:
                                 p['tags'] = [new_val if x==t else x for x in p['tags']]
                         atomic_save()
                         st.rerun()
                 
                 # Delete Button (Small X)
                 if c_del.button("✖", key=f"del_tag_{i}"):
                     st.session_state.tags.pop(i)
                     st.rerun()
    
    if st.session_state.clicked_date:
        if st.button("Clear Date"):
            st.session_state.clicked_date = None
            st.rerun() 


            
    # --- 6. RECYCLE BIN (Sidebar Bottom) ---
    st.markdown("---")
    
    # Custom Recycle Bin Icon
    res_bin_path = "/Users/pampan/.gemini/antigravity/brain/4499dd3b-5597-468b-8851-f1d47790ac74/pixel_art_trash_klein_yellow_1770467965524.png"
    
    # Read Image as Base64 for HTML embedding
    import base64
    with open(res_bin_path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()

    # Define Dialog Function
    @st.dialog("🗑️ RECYCLE BIN")
    def open_recycle_bin():
        c_hdr1, c_hdr2 = st.columns([0.85, 0.15])
        with c_hdr1:
            # Just show the icon to unify with sidebar, title is already in decorator
            st.markdown(f'<img src="data:image/png;base64,{b64_string}" width="40">', unsafe_allow_html=True)
        with c_hdr2:
            if st.button("❌", key="close_bin_dialog", help="Close"):
                st.rerun()

        if 'deleted_projects' not in st.session_state or not st.session_state.deleted_projects:
            st.markdown("<div style='text-align:center; padding:40px; font-family: VT323; font-size: 20px;'>THE BIN IS EMPTY!</div>", unsafe_allow_html=True)
            return
            
        st.markdown("---")
        if 'bin_expanded' not in st.session_state:
            st.session_state.bin_expanded = set()
            
        # Create a copy of the list to iterate safely
        for p in list(st.session_state.deleted_projects):
            p_id = p.get('id')
            with st.container(border=True):
                # 4 Columns: [Goal] [Details] [Restore] [Delete]
                c1, c2, c3, c4 = st.columns([0.34, 0.22, 0.22, 0.22])
                
                c1.markdown(f"**{p['goal']}**")
                
                # 1. DETAILS
                is_expanded = p_id in st.session_state.bin_expanded
                if c2.button("DETAILS" if not is_expanded else "HIDE", key=f"det_{p_id}", use_container_width=True):
                    if is_expanded: st.session_state.bin_expanded.remove(p_id)
                    else: st.session_state.bin_expanded.add(p_id)
                    st.rerun()
                
                # 2. RESTORE
                if c3.button("RESTORE", key=f"rest_{p_id}", use_container_width=True):
                    if 'deleted_at' in p: del p['deleted_at']
                    st.session_state.projects.append(p)
                    st.session_state.deleted_projects = [x for x in st.session_state.deleted_projects if x.get('id') != p_id]
                    atomic_save()
                    st.rerun()
                
                # 3. DELETE (Permanent)
                if c4.button("DELETE", key=f"perm_del_{p_id}", type="primary", use_container_width=True):
                    st.session_state.deleted_projects = [x for x in st.session_state.deleted_projects if x.get('id') != p_id]
                    atomic_save()
                    st.rerun()
                
                # Details Section (Conditional)
                if p_id in st.session_state.bin_expanded:
                    st.markdown("---")
                    deleted_at = p.get('deleted_at', 'Unknown')
                    if isinstance(deleted_at, str) and "T" in deleted_at:
                        try:
                            dt_obj = datetime.fromisoformat(deleted_at)
                            deleted_at = dt_obj.strftime("%Y-%m-%d %H:%M")
                        except: pass
                    
                    st.markdown(f"""
                    <div style="font-family: 'VT323', monospace; color: #002FA7; line-height: 1.4; padding: 10px; background: #E2E8F0; border: 2px solid #002FA7;">
                        <p style="margin: 0; font-size: 1.1rem;">📅 <b>PERIOD:</b> {p['start_date'].strftime('%Y-%m-%d') if hasattr(p['start_date'], 'strftime') else p['start_date']} → {p['end_date'].strftime('%Y-%m-%d') if hasattr(p['end_date'], 'strftime') else p['end_date']}</p>
                        <p style="margin: 0; font-size: 1.1rem;">🗑️ <b>DELETED ON:</b> {deleted_at}</p>
                        <hr style="margin: 10px 0; opacity: 0.3; border-color: #002FA7;">
                        <p style="margin-bottom: 5px;">✅ <b>TASKS ({len(p['tasks'])}):</b></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for t in p['tasks']:
                        check = "☑️" if t['completed'] else "⬜"
                        st.markdown(f"<div style='font-family: VT323; margin-left: 20px; color: #475569;'>{check} {t['task']}</div>", unsafe_allow_html=True)
                    
                    st.caption(f"Original ID: {p_id}")

    # Sidebar Layout: Icon (Left) | Buttons (Right)
    c_bin_icon, c_bin_btn = st.columns([0.3, 0.7])
    
    with c_bin_icon:
        st.markdown(f'''
        <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
            <img src="data:image/png;base64,{b64_string}" width="60" style="object-fit: contain;">
        </div>
        ''', unsafe_allow_html=True)
        
    with c_bin_btn:
        st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
        # Nested columns for side-by-side buttons
        btn_c1, btn_c2 = st.columns([0.5, 0.5])
        if btn_c1.button("OPEN BIN", key="btn_open_recycle_bin", use_container_width=True):
            open_recycle_bin()
        if btn_c2.button("CLEAN ALL", key="btn_sidebar_clean_bin", use_container_width=True, type="secondary"):
            st.session_state.deleted_projects = []
            st.rerun()
    
    # Backup
    st.markdown("---")
    d_json = json.dumps(st.session_state.projects, default=str, indent=2)
    
    # Force styling for Backup Button to match and be centered
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] div.stDownloadButton button {
        background-color: #F9DC24 !important;
        color: #002FA7 !important;
        border: 2px solid #002FA7 !important;
        box-shadow: 4px 4px 0px #000000 !important;
        font-family: 'VT323', monospace !important;
        font-size: 20px !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        justify-content: center !important; /* Critical for text centering */
        width: 100% !important;
        margin: 0 auto !important;
        display: flex !important;
        align-items: center !important;
    }
    section[data-testid="stSidebar"] div.stDownloadButton button:hover {
        background-color: #FFFFFF !important;
        transform: translate(2px, 2px) !important;
        box-shadow: 2px 2px 0px #000000 !important;
    }
    div[data-testid="stDownloadButton"] {
        text-align: center !important;
        justify-content: center !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.download_button("💾 Backup Data", d_json, "pacer.json", "application/json", use_container_width=True)

# --- Logic: Review Dashboard (Restored from review.py) ---
# render_review_dashboard is imported from review.py

# --- Main Layout ---
# Apply Search Filter
filtered_projects = st.session_state.projects
if search_query:
    q = search_query.lower()
    filtered_projects = [
        p for p in st.session_state.projects 
        if q in p['goal'].lower() 
        or any(q in t.lower() for t in p.get('tags', []))
    ]

# Initialize Calendar State
if 'calendar_date' not in st.session_state:
    st.session_state.calendar_date = datetime.now()

# Main Content Area (Full Width)
st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)





view_mode = st.session_state.view_mode

# 1. CALENDAR VIEW
if view_mode == "Calendar":
    
    # Function to handle date navigation
    def val_navigate(direction):
        if direction == 'back':
            st.session_state.calendar_date = st.session_state.calendar_date - relativedelta(months=1)
        elif direction == 'forward':
            st.session_state.calendar_date = st.session_state.calendar_date + relativedelta(months=1)
        elif direction == 'today':
            st.session_state.calendar_date = datetime.now()
    
    # Dynamic Title
    current_month_str = st.session_state.calendar_date.strftime("%B %Y")
    
    # Custom CSS for Calendar Navigation (High Contrast)
    st.markdown("""
    <style>
    /* Specific styling for the Prev/Next buttons */
    /* Target buttons within columns directly above the calendar */
    div[data-testid="stHorizontalBlock"] button {
        background-color: #F9DC24 !important; /* Yellow Background */
        color: #002FA7 !important; /* Blue Text */
        border: 2px solid #002FA7 !important;
        box-shadow: 2px 2px 0px #000000 !important;
        font-family: 'VT323', monospace !important;
        font-size: 24px !important;
        line-height: 1 !important;
        padding: 0px !important;
        min-height: 48px !important; /* Match Title Height */
    }
    div[data-testid="stHorizontalBlock"] button:hover {
        background-color: #FFFFFF !important;
        transform: translate(2px, 2px) !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Pixel Art Calendar Header (Standalone) ---
    c_prev, c_title, c_next = st.columns([0.15, 0.7, 0.15])
    
    with c_prev:
        if st.button("◀", key="nav_back", help="Previous Month", use_container_width=True):
            val_navigate('back')
            st.rerun()
            
    with c_title:
        st.markdown(f'''
        <div style="
            text-align: center; 
            font-family: 'VT323', monospace; 
            font-size: 36px; 
            font-weight: bold; 
            background-color: #002FA7; 
            color: #F9DC24; 
            text-transform: uppercase;
            letter-spacing: 2px;
            line-height: 48px;
            /* Border and Shadow removed */
        ">
            {current_month_str}
        </div>
        ''', unsafe_allow_html=True)
        
    with c_next:
        if st.button("▶", key="nav_fwd", help="Next Month", use_container_width=True):
            val_navigate('forward')
            st.rerun()

    # Spacer
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
    events = []
    today = datetime.now().date()
    
    for p in filtered_projects:
        # --- Restored Color Logic ---
        status = p.get('status', 'Not Started')
        vis_end = (p['end_date'] + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) \
                  if isinstance(p['end_date'], datetime) else p['end_date'] + timedelta(days=1)
        
        # Calculate metrics for color
        start_dw = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
        end_dw = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
        pct_exec = calculate_completion(p['tasks'])
        remaining_days = (end_dw - today).days + 1
        
        is_overdue = remaining_days <= 0 and pct_exec < 1.0
        is_urgent = remaining_days <= 3 and remaining_days > 0 and pct_exec < 1.0
        is_completed = (status == "Completed")
        is_not_started = today < start_dw
        
        # Pixel Art Palette (Primary Colors)
        if is_completed:
            bg_color = "#E0E0E0"    # Light Grey
            border_color = "#757575"
            text_color = "#424242"
            title_prefix = "✔ "
        elif is_overdue:
            bg_color = "#FFCDD2"    # Red
            border_color = "#C62828"
            text_color = "#B71C1C"
            title_prefix = "🔴 "
        elif is_not_started:
            bg_color = "#BBDEFB"    # Blue
            border_color = "#1565C0"
            text_color = "#0D47A1"
            title_prefix = "⏳ "
        else:
            # Active / In Progress
            bg_color = "#FFF9C4"    # Yellow
            border_color = "#FBC02D"
            text_color = "#E65100"
            title_prefix = "⚠️ " if is_urgent else ""

        title = f"{title_prefix}{p['goal']} ({int(pct_exec*100)}%)"

        evt = {
            "title": title,
            "start": p['start_date'].strftime("%Y-%m-%d"),
            "end": vis_end.strftime("%Y-%m-%d"),
            "backgroundColor": bg_color,
            "borderColor": border_color,
            "textColor": text_color,
            "extendedProps": {
                "projectId": p.get('id', ''),
                "status": status,
                "description": p.get('description', '')
            }
        }
        events.append(evt)

    # Calendar Rendering
    pixel_art_css = """
    .fc-header-toolbar { display: none !important; }
    .fc-daygrid-day-top { flex-direction: row; }
    .fc-daygrid-day-number { 
        font-family: 'VT323', monospace; 
        font-size: 20px; 
        color: #002FA7; 
        padding: 4px;
        text-decoration: none !important;
    }
    .fc-col-header-cell-cushion { 
        font-family: 'VT323', monospace; 
        font-size: 24px; 
        font-weight: bold; 
        color: #002FA7; 
        text-transform: uppercase;
        padding-bottom: 8px;
    }
    .fc-theme-standard td, .fc-theme-standard th {
        border: 3px solid #002FA7 !important; /* Thick Grid Lines */
    }
    .fc-daygrid-day-frame {
        border: none !important; /* Avoid double borders */
    }
    .fc .fc-daygrid-day.fc-day-today {
        background-color: #F9DC24 !important; /* Bright Yellow Highlight */
        background-image: linear-gradient(45deg, #F9DC24 25%, #FFF176 25%, #FFF176 50%, #F9DC24 50%, #F9DC24 75%, #FFF176 75%, #FFF176 100%);
        background-size: 10px 10px;
    }
    .fc-daygrid-event {
        border: 2px solid #000000 !important;
        box-shadow: 2px 2px 0px 0px rgba(0,0,0,0.5) !important;
        border-radius: 0px !important;
        padding: 2px 4px !important;
        font-family: 'VT323', monospace !important;
        font-size: 16px !important;
    }
    .fc-scrollgrid {
        border: 4px solid #002FA7 !important; /* Outer Border */
    }
    @media (prefers-color-scheme: dark) {
        .fc-daygrid-day {
            background-color: #E2E8F0 !important; /* Light gray for days in dark mode */
        }
        .fc-col-header-cell {
            background-color: #E2E8F0 !important;
        }
    }
    """
    
    init_date = st.session_state.calendar_date.strftime("%Y-%m-%d")
    
    opts = {
        "headerToolbar": False,
        "initialView": "dayGridMonth",
        "initialDate": init_date,
        "selectable": True,
        "editable": False,
        "timeZone": "local",
        "height": "750px"
    }
    
    calendar_callbacks = ["eventClick", "dateClick"]
    cal = calendar(events=events, options=opts, callbacks=calendar_callbacks, key=f"cal_{st.session_state.calendar_version}_{init_date}", custom_css=pixel_art_css)
    
    # Interaction Logic
    if cal:
        if cal.get("eventClick"):
             event_data = cal["eventClick"].get("event", {})
             extended_props = event_data.get("extendedProps", {})
             cid = extended_props.get("projectId")
             if cid:
                 st.session_state.selected_project_id = cid
                 st.session_state.calendar_version += 1
                 st.rerun()
        if cal.get("dateClick"):
            dstr = cal["dateClick"]["date"]
            try:
                val = datetime.strptime(dstr, "%Y-%m-%d")
                if st.session_state.clicked_date != val:
                    st.session_state.clicked_date = val
                    st.session_state.selected_project_id = None
                    st.rerun()
            except: pass

# 3. REVIEW DASHBOARD (Replaces List)
elif view_mode == "Review":
    # Clear Calendar selection when in Review
    st.session_state.selected_project_id = None
    
    # OVERRIDE CSS for Review Page (Low Saturation, Easy on Eyes)
    st.markdown("""
    <style>
    .stApp {
        background-color: #F0F4F8 !important; /* Soft Blue-Grey */
        color: #002FA7 !important; /* Dark Blue Text for Contrast */
    }
    /* Ensure all headers/text contrast heavily with the light background */
    h1, h2, h3, h4, h5, h6, p, li, span, label, div[data-testid="stMarkdownContainer"] {
        color: #002FA7 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    render_review_dashboard(filtered_projects)

# --- 7. CONGRATULATIONS MODAL (Mutually Exclusive with Project Dialog) ---
if st.session_state.get('celebrate_project'):
    @st.dialog("🎉 MISSION ACCOMPLISHED!")
    def show_congrats_dialog():
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; font-family: 'VT323', monospace;">
            <div style="font-size: 5rem; margin-bottom: 20px;">🏆</div>
            <h1 style="color: #002FA7; font-size: 3rem; margin-bottom: 10px; text-transform: uppercase;">Congratulations!</h1>
            <p style="font-size: 1.6rem; color: #475569; margin-bottom: 30px;">
                YOU HAVE MASTERED THIS PROJECT WITH GREAT RHYTHM!
            </p>
            <div style="background: #F9DC24; color: #002FA7; padding: 15px; border: 3px solid #002FA7; font-size: 1.4rem; font-weight: bold; margin-bottom: 20px;">
                MISSION REWARD UNLOCKED 🔓
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("COLLECT REWARD & CLOSE", use_container_width=True, type="primary"):
            st.session_state.celebrate_project = None
            st.rerun()

    show_congrats_dialog()

# --- 8. PROJECT DIALOG (If not celebrating) ---
elif view_mode == "Calendar" and st.session_state.selected_project_id:
    if st.session_state.selected_project_id == "DRAFT":
        show_new_project_dialog()
    else:
        show_project_dialog(st.session_state.selected_project_id)
