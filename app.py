import streamlit as st
import pandas as pd
import sys
import os
import time
import base64
import uuid
import json
import textwrap
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from streamlit_calendar import calendar
from utils import generate_checklist, extract_tags
from review import render_review_dashboard
from persistence import load_data, save_data, load_focus_data, save_focus_data, load_tags, save_tags
from styles import GLOBAL_STYLES

# Ensure local modules are found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# --- Global Assets ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RES_BIN_PATH = os.path.join(_BASE_DIR, "assets", "recycle_bin.png")
RES_BIN_SMALL_PATH = os.path.join(_BASE_DIR, "assets", "recycle_bin_small.png")

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

# --- Persistence Initialization ---
if 'show_bin' not in st.session_state: st.session_state.show_bin = False

# --- Top-Level Dialog Definitions (Streamlit Best Practice) ---

@st.dialog("RECYCLE BIN")
def open_recycle_bin():
    # SURGICAL CSS: hide default header + force ALL bin action buttons identical via st-key targeting
    st.markdown("""
    <style>
    [data-testid="stDialogHeader"], 
    header[data-testid="stHeader"],
    .st-emotion-cache-1mf1b6k {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }
    /* Target ALL recycle bin action buttons by their st-key class prefix */
    [class*="st-key-top_det"] button,
    [class*="st-key-top_rest"] button,
    [class*="st-key-top_perm_del"] button {
        background-color: #F9DC24 !important;
        color: #002FA7 !important;
        border: 2px solid #002FA7 !important;
        box-shadow: 3px 3px 0px #000000 !important;
        font-weight: bold !important;
        font-family: 'VT323', monospace !important;
        font-size: 16px !important;
        text-transform: uppercase !important;
        border-radius: 0px !important;
        min-height: 38px !important;
        height: 38px !important;
        max-height: 38px !important;
        padding: 6px 16px !important;
        line-height: 1.2 !important;
    }
    [class*="st-key-top_det"] button:hover,
    [class*="st-key-top_rest"] button:hover,
    [class*="st-key-top_perm_del"] button:hover {
        background-color: #002FA7 !important;
        color: #F9DC24 !important;
        box-shadow: 1px 1px 0px #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    b64 = get_image_base64(RES_BIN_PATH)
    
    # UNIFIED HEADER: Perfect alignment between icon, title and X
    c_h1, c_h2 = st.columns([0.88, 0.12])
    with c_h1:
        st.markdown(f'''
        <div style="display: flex; align-items: center; gap: 15px; height: 35px;">
            <img src="data:image/png;base64,{b64}" width="32" style="image-rendering: pixelated;">
            <span style="font-family: 'VT323', monospace; font-size: 24px; color: #002FA7; font-weight: bold; text-transform: uppercase; line-height: 35px;">RECYCLE BIN</span>
        </div>
        ''', unsafe_allow_html=True)
    with c_h2:
        if st.button("❌", key="top_close_bin_dialog", use_container_width=True):
            st.session_state.show_bin = False
            st.rerun()
    
    st.markdown("<hr style='margin: 10px 0 20px 0; border: 1px dashed #002FA7; opacity: 0.3;'>", unsafe_allow_html=True)

    if 'deleted_projects' not in st.session_state or not st.session_state.deleted_projects:
        st.markdown("<div style='text-align:center; padding:40px; font-family: VT323; font-size: 20px;'>THE BIN IS EMPTY!</div>", unsafe_allow_html=True)
        return
        
    if 'bin_expanded' not in st.session_state:
        st.session_state.bin_expanded = set()
        
    for p in list(st.session_state.deleted_projects):
        p_id = p.get('id')
        with st.container(border=False):
            # Project name on its own line
            st.markdown(f"<div style='font-family: VT323; font-size: 18px; line-height: 1.3; padding: 4px 0;'><b>{p['goal']}</b></div>", unsafe_allow_html=True)
            # 3 equal-width buttons below
            btn1, btn2, btn3 = st.columns([1, 1, 1])
            
            if btn1.button("DETAILS", key=f"top_det_{p_id}", type="primary", use_container_width=True):
                if p_id not in st.session_state.bin_expanded:
                    st.session_state.bin_expanded.add(p_id)
                else:
                    st.session_state.bin_expanded.remove(p_id)
            
            if btn2.button("RESTORE", key=f"top_rest_{p_id}", type="primary", use_container_width=True):
                if 'deleted_at' in p: del p['deleted_at']
                st.session_state.projects.append(p)
                st.session_state.deleted_projects = [x for x in st.session_state.deleted_projects if x.get('id') != p_id]
                atomic_save()
                st.rerun()
            
            if btn3.button("DELETE", key=f"top_perm_del_{p_id}", type="primary", use_container_width=True):
                st.session_state.deleted_projects = [x for x in st.session_state.deleted_projects if x.get('id') != p_id]
                atomic_save()
                st.rerun()
            
            if p_id in st.session_state.bin_expanded:
                st.markdown("---")
                deleted_at = p.get('deleted_at', 'Unknown')
                st.markdown(f"""
                <div style="font-family: 'VT323', monospace; color: #002FA7; line-height: 1.4; padding: 10px; background: #E2E8F0; border: 2px solid #002FA7;">
                    <p style="margin: 0; font-size: 1.1rem;">📅 <b>PERIOD:</b> {p['start_date']} → {p['end_date']}</p>
                    <p style="margin: 0; font-size: 1.1rem;">🗑️ <b>DELETED ON:</b> {deleted_at}</p>
                </div>
                """, unsafe_allow_html=True)
@st.dialog("PROJECT DETAILS") # MASTER DIALOG: Shared by Calendar & Review
def show_project_dialog(proj_id):
    # SURGICAL CSS: ONLY hide the default header, don't touch margins of content
    st.markdown("""
    <style>
    [data-testid="stDialogHeader"], 
    header[data-testid="stHeader"],
    .st-emotion-cache-1mf1b6k {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    proj_id = str(proj_id)
    if 'projects' not in st.session_state:
        st.error("Session data missing.")
        return

    # Locate Project
    proj = next((x for x in st.session_state.projects if str(x.get('id')) == proj_id), None)
    
    if not proj:
        st.error(f"Project not found. ID: {proj_id}")
        if st.button("Close", key="err_close"): 
            st.session_state.selected_project_id = None
            st.rerun()
        return

    # UNIFIED HEADER: Title & X on one row
    c_h1, c_h2 = st.columns([0.88, 0.12])
    with c_h1:
        st.markdown(f"<div style='font-family: VT323; font-size: 24px; color: #002FA7; font-weight: bold; text-transform: uppercase; height: 35px; line-height: 35px;'>PROJECT DETAILS</div>", unsafe_allow_html=True)
    with c_h2:
        if st.button("❌", key=f"close_x_{proj_id}", use_container_width=True):
            st.session_state.selected_project_id = None
            st.rerun()
    
    st.markdown("<hr style='margin: 10px 0 20px 0; border: 1px dashed #002FA7; opacity: 0.3;'>", unsafe_allow_html=True)

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
            
    # --- PROGRESS & RHYTHM VISUALIZATION ---
    try:
        pct_exec = calculate_completion(proj['tasks'])
        
        # Time Calculations
        start_d = proj['start_date'].date() if isinstance(proj['start_date'], datetime) else proj['start_date']
        end_d = proj['end_date'].date() if isinstance(proj['end_date'], datetime) else proj['end_date']
        today_d = datetime.now().date()
        
        total_days = max((end_d - start_d).days + 1, 1)
        remaining_days = (end_d - today_d).days + 1
        
        if today_d < start_d: remaining_days = total_days
        elif today_d > end_d: remaining_days = 0
        else: remaining_days = max(0, remaining_days)
        
        pct_remaining = max(0.0, min(1.0, remaining_days / total_days))
        pct_elapsed = 1.0 - pct_remaining
        
        # Hourglass Sand Calculations (Restored Logic)
        sand_top = int(pct_remaining * 100)
        sand_bottom = int(pct_elapsed * 100)
        
        # Status Logic
        is_behind = pct_elapsed > pct_exec
        rhythm_gap = abs(pct_elapsed - pct_exec)
        
        is_urgent = remaining_days <= 3 and remaining_days > 0 and pct_exec < 1.0
        is_overdue = remaining_days <= 0 and pct_exec < 1.0
        
        # Pulse & Color Logic (Red/Green=Static, Orange=Medium, Yellow=Slow)
        if is_overdue:
            time_color = "#EF4444"  # Red
            pulse_class = ""  # STATIC — fact statement
        elif is_urgent:
            time_color = "#F59E0B"  # Orange
            pulse_class = "pulse-medium"  # needs attention
        elif is_behind:
            time_color = "#FBBF24"  # Yellow
            pulse_class = "pulse-slow"
        else:
            time_color = "#10B981"  # Green
            pulse_class = ""  # STATIC — plenty of time
            
        exec_color = "#10B981" if pct_exec >= pct_elapsed else "#6B7280"

        # Build combined hourglass + beaker HTML
        sand_stream_html = ""
        if pct_remaining > 0.05 and pct_remaining < 0.95:
            sand_stream_html = f'<line x1="25" y1="35" x2="25" y2="50" stroke="{time_color}" stroke-width="2" stroke-dasharray="3,3" opacity="0.5"/>'
        
        # Beaker fill calculation (from bottom up)
        beaker_fill_h = int(pct_exec * 40)  # max 40px fill height
        beaker_fill_y = 60 - beaker_fill_h  # y position (bottom=60, top=20)
        exec_pct_int = int(pct_exec * 100)
        
        combined_html = f"""<style>
@keyframes pulse-slow {{0%, 100% {{ transform: scale(1); opacity: 1; }} 50% {{ transform: scale(1.02); opacity: 0.9; }}}}
@keyframes pulse-medium {{0%, 100% {{ transform: scale(1); opacity: 1; }} 50% {{ transform: scale(1.04); opacity: 0.85; }}}}
.pulse-slow {{ animation: pulse-slow 3s ease-in-out infinite; }}
.pulse-medium {{ animation: pulse-medium 1.5s ease-in-out infinite; }}
.progress-panel {{ display: flex; align-items: center; gap: 0; padding: 12px 16px; background: linear-gradient(135deg, #1a1c24 0%, #2d3748 100%); border-radius: 12px; margin: 16px 0; }}
.panel-left, .panel-right {{ flex: 1; display: flex; align-items: center; gap: 12px; }}
.panel-divider {{ width: 1px; background: rgba(255,255,255,0.15); height: 70px; margin: 0 14px; flex-shrink: 0; }}
.svg-icon {{ width: 50px; height: 65px; min-width: 50px; }}
.svg-icon svg {{ width: 100%; height: 100%; }}
.panel-info {{ font-family: 'VT323', monospace; }}
.panel-label {{ font-size: 0.75em; color: #9CA3AF; text-transform: uppercase; margin-bottom: 2px; }}
.panel-value {{ font-size: 1.3em; font-weight: bold; }}
.panel-badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.7em; font-weight: 600; margin-top: 4px; }}
.badge-ok {{ background: #10B981; color: white; }}
.badge-warn {{ background: {time_color}; color: white; }}
</style>
<div class="progress-panel {pulse_class}"><div class="panel-left"><div class="svg-icon"><svg viewBox="0 0 50 70" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5 5 L45 5 L45 10 L30 35 L45 60 L45 65 L5 65 L5 60 L20 35 L5 10 Z" stroke="{time_color}" stroke-width="2" fill="none"/><path d="M10 10 L40 10 L28 {35 - sand_top * 0.2} L22 {35 - sand_top * 0.2} Z" fill="{time_color}" opacity="0.7"/><path d="M10 60 L40 60 L28 {60 - sand_bottom * 0.2} L22 {60 - sand_bottom * 0.2} Z" fill="{time_color}" opacity="0.9"/>{sand_stream_html}</svg></div><div class="panel-info"><div class="panel-label">⏳ Time Left</div><div class="panel-value" style="color:{time_color}">{remaining_days}d ({int(pct_remaining*100)}%)</div><div class="panel-badge {'badge-ok' if not is_behind else 'badge-warn'}">{'✅ On Rhythm' if not is_behind else f'⚠️ Gap {int(rhythm_gap*100)}%'}</div></div></div><div class="panel-divider"></div><div class="panel-right"><div class="svg-icon"><svg viewBox="0 0 50 70" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="10" y="5" width="30" height="4" rx="1" fill="#9CA3AF" opacity="0.6"/><path d="M13 9 L13 62 Q13 65 16 65 L34 65 Q37 65 37 62 L37 9 Z" stroke="{exec_color}" stroke-width="2" fill="none"/><rect x="15" y="{beaker_fill_y}" width="20" height="{beaker_fill_h}" fill="{exec_color}" opacity="0.7" rx="1"/><line x1="15" y1="25" x2="18" y2="25" stroke="#9CA3AF" stroke-width="1" opacity="0.4"/><line x1="15" y1="35" x2="18" y2="35" stroke="#9CA3AF" stroke-width="1" opacity="0.4"/><line x1="15" y1="45" x2="18" y2="45" stroke="#9CA3AF" stroke-width="1" opacity="0.4"/><line x1="15" y1="55" x2="18" y2="55" stroke="#9CA3AF" stroke-width="1" opacity="0.4"/></svg></div><div class="panel-info"><div class="panel-label">🧪 Execution</div><div class="panel-value" style="color:{exec_color}">{exec_pct_int}%</div><div class="panel-badge" style="background:{exec_color};color:white">{'🏁 DONE' if pct_exec >= 1.0 else f'📊 {len([t for t in proj["tasks"] if t["completed"]])}/{len(proj["tasks"])} tasks'}</div></div></div></div>"""
        st.markdown(combined_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Time Widget Error: {e}")
    
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

    st.divider()
    
    # --- CHECKPOINTS (Tasks) ---
    st.markdown("<div style='font-family: VT323; font-size: 20px; color: #002FA7; margin-bottom: 10px;'>CHECKPOINTS</div>", unsafe_allow_html=True)
    
    # Checkpoints
    for i, t in enumerate(proj['tasks']):
        col_a, col_b, col_c = st.columns([0.06, 0.82, 0.12])
        with col_a:
            is_checked = st.checkbox("", value=t['completed'], key=f"dlg_chk_{t.get('id', i)}")
            if is_checked != t['completed']:
                t['completed'] = is_checked
                atomic_save()
                all_done = all(task['completed'] for task in proj['tasks'])
                if all_done and is_checked:
                    proj['completed_at'] = datetime.now()
                    atomic_save()
                    st.session_state.celebrate_project = proj_id
                st.rerun()
        with col_b:
            task_name = t.get('task', t.get('name', 'Unnamed'))
            new_name = st.text_input("task", value=task_name, key=f"edit_chk_{proj_id}_{i}", label_visibility="collapsed")
            if new_name != task_name:
                t['task'] = new_name
                atomic_save()
        with col_c:
            if st.button("✕", key=f"dlg_del_t_{t.get('id', i)}", help="Remove", use_container_width=True):
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
    
    # --- DELETE SECTION (Recycle Bin Icon + Button aligned) ---
    bin_b64 = get_image_base64(RES_BIN_SMALL_PATH)
    bin_icon = f'<img src="data:image/png;base64,{bin_b64}" width="32" style="image-rendering:pixelated;vertical-align:middle">' if bin_b64 else '🗑️'
    st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin:8px 0;"><span>{bin_icon}</span><span style="font-family:VT323,monospace;font-size:14px;color:#9CA3AF;">Move this project to the Recycle Bin</span></div>', unsafe_allow_html=True)
    if st.button("🗑️ THROW IN BIN", key=f"dlg_del_proj_{proj_id}", type="primary", use_container_width=True):
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

@st.dialog("CREATE NEW PROJECT")
def show_new_project_dialog():
    # SURGICAL CSS: ONLY hide the default header, don't touch margins of content
    st.markdown("""
    <style>
    [data-testid="stDialogHeader"], 
    header[data-testid="stHeader"],
    .st-emotion-cache-1mf1b6k {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)
    # UNIFIED HEADER: Title & X on one row
    c_h1, c_h2 = st.columns([0.88, 0.12])
    with c_h1:
        st.markdown(f"<div style='font-family: VT323; font-size: 24px; color: #002FA7; font-weight: bold; text-transform: uppercase; height: 35px; line-height: 35px;'>CREATE NEW PROJECT</div>", unsafe_allow_html=True)
    with c_h2:
        if st.button("❌", key="close_new_proj_dialog", use_container_width=True):
            st.session_state.selected_project_id = None
            st.rerun()
    
    st.markdown("<hr style='margin: 10px 0 20px 0; border: 1px dashed #002FA7; opacity: 0.3;'>", unsafe_allow_html=True)

    new_goal = st.text_input("Project Goal", placeholder="What do you want to achieve?", key="dlg_new_project_goal")
    
    col1, col2 = st.columns(2)
    with col1:
        start_d = st.date_input("Start Date", value=datetime.now(), key="dlg_new_project_start")
    with col2:
        end_d = st.date_input("Deadline", value=datetime.now() + timedelta(days=7), key="dlg_new_project_end")
    
    all_tags = st.session_state.get('tags', [])
    sel_tags = st.multiselect("Tags", all_tags, key="dlg_new_project_tags")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("CREATE PROJECT", type="primary", use_container_width=True):
            if new_goal:
                create_project(new_goal, start_d, end_d, tags=sel_tags)
                st.session_state.selected_project_id = None
                st.rerun()
            else:
                st.error("Please enter a goal.")
    with c2:
        if st.button("CANCEL", use_container_width=True):
            st.session_state.selected_project_id = None
            st.rerun()

@st.dialog("MISSION ACCOMPLISHED")
def show_congrats_dialog():
    # SURGICAL CSS: ONLY hide the default header, don't touch margins of content
    st.markdown("""
    <style>
    [data-testid="stDialogHeader"], 
    header[data-testid="stHeader"],
    .st-emotion-cache-1mf1b6k {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)
    # UNIFIED HEADER: Title & X on one row
    c_h1, c_h2 = st.columns([0.88, 0.12])
    with c_h1:
        st.markdown(f"<div style='font-family: VT323; font-size: 24px; color: #002FA7; font-weight: bold; text-transform: uppercase; height: 35px; line-height: 35px;'>MISSION ACCOMPLISHED</div>", unsafe_allow_html=True)
    with c_h2:
        if st.button("❌", key="top_close_congrats", use_container_width=True):
            st.session_state.celebrate_project = None
            st.session_state.selected_project_id = None
            st.rerun()
    
    st.markdown("<hr style='margin: 10px 0 20px 0; border: 1px dashed #002FA7; opacity: 0.3;'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align: center; padding: 20px; font-family: 'VT323', monospace;">
        <div style="font-size: 5rem; margin-bottom: 20px;">🏆</div>
        <h1 style="color: #002FA7; font-size: 3rem; text-transform: uppercase;">Congratulations!</h1>
        <p style="font-size: 1.6rem; color: #475569;">YOU HAVE MASTERED THIS PROJECT!</p>
    </div>
    """, unsafe_allow_html=True)



# --- Config & Style ---
st.set_page_config(page_title="Life OS · Pacer 3.4", layout="wide", page_icon="🌑")

# --- CUSTOM CSS INJECTION (Date Scroll + Dialog Unification) ---
st.markdown("""
<style>
    /* Date Picker Popover Fix */
    div[data-testid="stDateInput"] div[data-baseweb="popover"],
    div[data-baseweb="popover"] {
        max-height: 450px !important;
        overflow: auto !important;
    }
    .stDateInput input {
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)

# --- Session State ---
if 'projects' not in st.session_state or 'deleted_projects' not in st.session_state:
    st.session_state.projects, st.session_state.deleted_projects = load_data()

if 'focus_sessions' not in st.session_state:
    st.session_state.focus_sessions = load_focus_data()

if 'tags' not in st.session_state:
    st.session_state.tags = load_tags()

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

if 'new_goal_input' not in st.session_state:
    st.session_state.new_goal_input = ""

def atomic_save():
    save_data(st.session_state.projects, st.session_state.deleted_projects)
    if 'focus_sessions' in st.session_state:
        save_focus_data(st.session_state.focus_sessions)

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

# --- Global Resources (using paths defined at top) ---


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

# --- Helper: Focus Timer Fragment (Self-Contained Rerunning) ---
@st.fragment(run_every=1)
def render_focus_timer():
    # Ensure Session State
    if 'focus_mode_active' not in st.session_state: st.session_state.focus_mode_active = False
    if 'focus_end_time' not in st.session_state: st.session_state.focus_end_time = datetime.now()
    if 'focus_duration' not in st.session_state: st.session_state.focus_duration = 25
    
    # Calculate State for Initial Render
    remaining_min = st.session_state.focus_duration
    clock_status = "READY"
    clock_color = "#FFFFFF"
    display_time = f"{remaining_min:02d}:00"
    
    end_timestamp_iso = ""
    
    if st.session_state.focus_mode_active:
        clock_status = "ACTIVE"
        clock_color = "#F9DC24"
        now = datetime.now()
        if now < st.session_state.focus_end_time:
             diff = st.session_state.focus_end_time - now
             t_sec = int(diff.total_seconds())
             mm = t_sec // 60
             ss = t_sec % 60
             display_time = f"{mm:02d}:{ss:02d}"
             end_timestamp_iso = st.session_state.focus_end_time.isoformat()
        else:
             # Timer finished naturally
             st.session_state.focus_mode_active = False
             
             # RECORD THE SESSION IMMEDIATELY
             new_session = {
                 "date": datetime.now(),
                 "duration": st.session_state.focus_duration,
                 "project_id": st.session_state.get('selected_project_id')
             }
             if 'focus_sessions' not in st.session_state: st.session_state.focus_sessions = []
             st.session_state.focus_sessions.append(new_session)
             save_focus_data(st.session_state.focus_sessions)
             
             clock_status = "DONE"
             display_time = "00:00"
             # Optionally trigger a notification/toast
             st.toast(f"✅ Focus Session ({st.session_state.focus_duration}m) Complete!", icon="🏆")

    with st.container(border=True):
        st.markdown('<div class="sidebar-module-title">FOCUS TIMER</div>', unsafe_allow_html=True)
        
        # Unique ID for JS targeting
        clock_id = f"timer_{uuid.uuid4().hex[:8]}"
        
        # Render Clock HTML
        st.markdown(f'''
        <div class="digital-clock-container">
            <div class="digital-clock-label">{clock_status}</div>
            <div id="{clock_id}" class="digital-clock-display" style="color:{clock_color}; text-shadow: 2px 2px 0px #000;">
                {display_time}
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # INJECT JAVASCRIPT FOR COUNTDOWN (Only if Active)
        if st.session_state.focus_mode_active and end_timestamp_iso:
            st.markdown(f"""
            <script>
            (function() {{
                const clock = document.getElementById('{clock_id}');
                const endTime = new Date("{end_timestamp_iso}").getTime();
                
                function updateTimer() {{
                    const now = new Date().getTime();
                    const distance = endTime - now;
                    
                    if (distance < 0) {{
                        clock.innerText = "00:00";
                        clearInterval(interval);
                        return;
                    }}
                    
                    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
                    
                    const mStr = minutes < 10 ? "0" + minutes : minutes;
                    const sStr = seconds < 10 ? "0" + seconds : seconds;
                    clock.innerText = mStr + ":" + sStr;
                }}
                
                const interval = setInterval(updateTimer, 1000);
            }})();
            </script>
            """, unsafe_allow_html=True)
        
        # Controls
        if st.session_state.focus_mode_active:
            if st.button("STOP", key="btn_stop_focus", type="primary", use_container_width=True):
                st.session_state.focus_mode_active = False
                
                # RECORD PARTIAL SESSION IF > 1 MINUTE
                end_time_actual = datetime.now()
                # Calculate elapsed time based on original duration minus remaining
                # But we don't store start time explicitly in session_state, we store end_time.
                # Elapsed = Duration - (End_Time - Now)
                time_left = st.session_state.focus_end_time - end_time_actual
                time_left_min = time_left.total_seconds() / 60.0
                elapsed_min = st.session_state.focus_duration - time_left_min
                
                # Lower threshold to 0.1 minutes (6 seconds) to act as "any significant activity"
                if elapsed_min >= 0.1:
                    new_session = {
                         "date": end_time_actual,
                         "duration": max(1, int(elapsed_min)), # Store at least 1 minute if it's small but significant? Or store float? 
                         # Requirement is minutes integer usually. Let's round up to 1 if it's > 6 seconds.
                         "project_id": st.session_state.get('selected_project_id')
                    }
                    if 'focus_sessions' not in st.session_state: st.session_state.focus_sessions = []
                    st.session_state.focus_sessions.append(new_session)
                    save_focus_data(st.session_state.focus_sessions)
                    st.toast(f"✅ Focus Session ({max(1, int(elapsed_min))}m) Recorded!", icon="💾")
                else:
                    st.toast("Focus session too short (< 6s) to record.", icon="⚠️")
                    
                st.rerun()
        else:
            # DATE PICKER STABILITY FIX: move number_input out of fragment if possible? 
            # Actually, the issue is likely global rerun. st.fragment shouldn't trigger full rerun unless we call st.rerun().
            # BUT inside st.fragment, any widget interaction triggers a rerun OF THE FRAGMENT.
            # If the user clicks "Start", we set focus_mode_active=True.
            
            f_dur = st.number_input("Duration (min)", 5, 120, st.session_state.focus_duration, step=5, label_visibility="collapsed")
            st.session_state.focus_duration = f_dur
            
            if st.button("START FOCUS", key="btn_start_focus", type="primary", use_container_width=True):
                 st.session_state.focus_mode_active = True
                 st.session_state.focus_end_time = datetime.now() + timedelta(minutes=st.session_state.focus_duration)
                 st.rerun()
                 st.rerun()

# --- DIALOGS MOVED TO TOP ---

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
    s_d = datetime.now()
    e_d = datetime.now() + timedelta(days=7)
    
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
        
        /* FIX: LIGHTEN SELECT BOX/MULTISELECT BACKGROUND */
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #000000 !important;
            border-color: #cccccc !important;
        }
        div[data-baseweb="select"] span {
            color: #000000 !important;
        }
        /* Dropdown menu items */
        ul[data-baseweb="menu"] {
            background-color: #ffffff !important;
        }
        ul[data-baseweb="menu"] li {
            color: #000000 !important;
        }
        
        /* FIX: DIALOG BORDERS - ADAPTIVE */
        div[role="dialog"], 
        div[data-testid="stDialog"], 
        div[data-testid="stModal"],
        section[tabindex="-1"] > div {
            /* Default (Light Mode) - Transparent/None */
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }

        /* Inner Content Styling */
        div[data-testid="stDialog"] > div,
        div[data-testid="stDialog"] > div > div {
             box-shadow: 0px 8px 24px rgba(0,0,0,0.15) !important;
             border-radius: 12px !important;
        }

        /* DARK MODE SPECIFIC FIX */
        @media (prefers-color-scheme: dark) {
            /* Force the dialog content to have a visible, lighter border instead of black */
            div[role="dialog"], 
            div[data-testid="stDialog"],
            section[tabindex="-1"] > div {
                border: 1px solid #E2E8F0 !important; /* Very Light Grey */
                outline: 1px solid transparent !important;
            }
            
            /* Target inner containers to ensure no black bleed */
            div[data-testid="stDialog"] > div,
            div[data-testid="stDialog"] > div > div {
                border: 1px solid #E2E8F0 !important; /* Very Light Grey */
                background-color: #1e293b !important; /* Ensure dark slate bg */
                color: #e2e8f0 !important; /* Ensure light text */
            }
            
            /* Ensure inputs inside dialogs are ALWAYS LIGHT (White) */
            div[data-testid="stDialog"] input,
            div[data-testid="stDialog"] textarea {
                background-color: #FFFFFF !important;
                color: #000000 !important;
                border: 1px solid #CCCCCC !important;
            }
            /* Also target stSelectbox/stMultiSelect trigger boxes in dialogs */
            div[data-testid="stDialog"] div[data-baseweb="select"] > div {
                background-color: #FFFFFF !important;
                color: #000000 !important;
            }
        }
        
        /* SURGICAL HIDE ALL DEFAULT DIALOG HEADERS */
        [data-testid="stDialogHeader"], 
        header[data-testid="stHeader"],
        .st-emotion-cache-1mf1b6k,
        button[aria-label="Close"] {
            display: none !important;
            height: 0 !important;
            visibility: hidden !important;
        }
        
        /* Specific content container typically has the background and border */
        section[data-testid="stDialog"] > div:first-child {
             border: none !important;
        }
        
        section[data-testid="stSidebar"] div.block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Small Buttons in Grids (Tags, Add, Open Bin) */
        section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] button {
            height: auto !important;
            padding: 4px 8px !important;
            min-height: 0px !important;
        }

        /* FORCE IDENTICAL CLOSE BUTTON STYLE FOR ALL DIALOGS (Review, Calendar, Bin) */
        /* Target only the ❌ close buttons by their st-key class containing 'close' */
        div[data-testid="stDialog"] [class*="st-key-"][class*="close"] button {
             /* Calendar Style Replication */
             background-color: transparent !important;
             color: #002FA7 !important;
             border: 2px solid #002FA7 !important;
             border-radius: 0px !important;
             box-shadow: 2px 2px 0px #002FA7 !important;
             font-family: 'VT323', monospace !important;
             font-weight: bold !important;
             height: auto !important;
             padding: 4px 10px !important;
             transition: all 0.1s ease !important;
        }
        div[data-testid="stDialog"] [class*="st-key-"][class*="close"] button:hover {
             transform: translate(1px, 1px) !important;
             box-shadow: 1px 1px 0px #002FA7 !important;
             background-color: #E0E7FF !important;
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
        
        /* HIDE DATE RANGE PICKER 'QUICK SELECT' (Choose a date range) */
        div[data-baseweb="calendar"] div[data-baseweb="select"] {
            display: none !important;
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
        d_color = "#5D4037"; d_label = "BALANCED"; d_icon = "TIME DEBT"
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
            <div class="passbook-row" title="🎯 RHYTHM SCORE (Reliability): The percentage of your projects that were completed ON TIME. Aim for 100%.">
                <span class="passbook-label" style="border-bottom: 1px dotted #F9DC24; cursor: help;">RHYTHM SCORE</span>
                <span class="passbook-large-val">{rhythm}</span>
                <span style="font-size:12px; color:{r_color}; font-weight:bold;">PTS</span>
            </div>
            <div class="passbook-row" title="⏳ TIME CREDIT/DEBT (Efficiency): Total days saved (+) or lost (-) compared to your planned schedules.">
                <span class="passbook-label" style="border-bottom: 1px dotted #F9DC24; cursor: help;">{d_icon}</span>
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
    # Rendered using st.fragment for non-blocking updates
    render_focus_timer()

    # --- 5. NEW PROJECT ---
    # REVERTED FRAGMENT: Direct rendering to prevent error loop / duplicate widget ID
    def on_sidebar_date_change():
        st.session_state.selected_project_id = None

    with st.container(border=True):
        st.markdown('<div class="sidebar-module-title">NEW MISSION</div>', unsafe_allow_html=True)
        
        st.caption("Select Dates")
        st.date_input(
            "Select Dates", value=[], key="sb_date_range", 
            format="MM/DD/YYYY", label_visibility="collapsed", on_change=on_sidebar_date_change
        )
        
        st.caption("Define Goal")
        st.text_input(
            "Goal", key="new_goal_input", placeholder="e.g. Run Marathon", label_visibility="collapsed"
        )
        
        st.caption("Assign Tags")
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
                 save_tags(st.session_state.tags)
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
                         
                         save_tags(st.session_state.tags)
                         atomic_save()
                         st.rerun()
                 
                 # Delete Button (Small X)
                 if c_del.button("✖", key=f"del_tag_{i}"):
                     st.session_state.tags.pop(i)
                     save_tags(st.session_state.tags)
                     st.rerun()
    
    if st.session_state.clicked_date:
        if st.button("Clear Date"):
            st.session_state.clicked_date = None
            st.rerun() 


            
    # --- 6. RECYCLE BIN (Sidebar Bottom) ---
    st.markdown("---")
    
    # Custom Recycle Bin Icon — use global path
    b64_string = get_image_base64(RES_BIN_PATH)

# --- REMOVED DIALOG DEFINITIONS FROM SIDEBAR ---

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
            st.session_state.show_bin = True
            st.rerun()
        if btn_c2.button("CLEAN ALL", key="btn_sidebar_clean_bin", use_container_width=True, type="secondary"):
            st.session_state.deleted_projects = []
            atomic_save()
            st.rerun()
    
    # Backup
    st.markdown("---")
    
    # PREPARE FULL BACKUP DATA
    backup_data = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "projects": st.session_state.projects,
        "deleted_projects": st.session_state.get('deleted_projects', []),
        "focus_sessions": st.session_state.get('focus_sessions', []),
        "tags": st.session_state.tags
    }
    d_json = json.dumps(backup_data, default=str, indent=2)
    
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
    
    st.download_button("💾 Backup Data", d_json, "pacer.json", "text/plain", use_container_width=True)

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
        st.session_state.selected_project_id = None # Clear selection
        if 'calendar_version' not in st.session_state:
            st.session_state.calendar_version = 0
        st.session_state.calendar_version += 1 # Force new key to prevent ghost clicks
        
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
    # selected_project_id reset removed to allow View button to work
    
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

# --- 7. MODAL DISPATCHER (Mutually Exclusive) ---
if st.session_state.show_bin:
    open_recycle_bin()
elif st.session_state.get('celebrate_project'):
    show_congrats_dialog()
elif st.session_state.selected_project_id:
    if st.session_state.selected_project_id == "DRAFT":
        show_new_project_dialog()
    else:
        show_project_dialog(st.session_state.selected_project_id)


# --- 8. CLEAN RE-RUN HANDLING ---
# (Removed the focus timer loop as it is now handled by st.fragment locally)
