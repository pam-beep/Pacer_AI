import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from persistence import save_data, load_journal, save_journal
from ai_suggestions import analyze_patterns, generate_suggestions
import uuid
import textwrap

# FIX: Light Mode Compatible Buttons for Review Dashboard
st.markdown("""
<style>
    /* Review Dashboard Buttons - Light Mode Fix */
    section[data-testid="stMain"] .stButton > button {
        background-color: #00CC96 !important;
        color: #FFFFFF !important;
        border: 1px solid #00AA7D !important;
        font-weight: 600 !important;
        min-width: 40px !important;
    }
    section[data-testid="stMain"] .stButton > button:hover {
        background-color: #00AA7D !important;
        color: #FFFFFF !important;
    }
    
    /* Download Button Fix */
    .stDownloadButton > button {
        background-color: #3B82F6 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button:hover {
        background-color: #2563EB !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper: Rich Detail Dialog (Editable) ---
@st.dialog("Project Details")
def view_project_dialog(p_id):
    p_id_str = str(p_id)
    if 'projects' not in st.session_state:
        st.error("Session data missing.")
        return
    proj = next((x for x in st.session_state.projects if str(x.get('id')) == p_id_str), None)
    if not proj:
        st.error(f"Project not found. ID: {p_id}")
        if st.button("Close"): st.rerun()
        return

    # --- Resources ---
    res_bin_path = "/Users/pampan/.gemini/antigravity/brain/4499dd3b-5597-468b-8851-f1d47790ac74/pixel_art_recycle_bin_transparent_1770466742660.png"
    import base64
    def get_img_b64(path):
        try:
            with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
        except: return ""

    # --- HEADER ---
    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        new_goal = st.text_input("Goal", value=proj['goal'], key=f"d_goal_{p_id}")
        if new_goal != proj['goal']:
            proj['goal'] = new_goal
            save_data(st.session_state.projects)
            st.rerun()
    with c2:
        # Simple status badge
        comp = sum(1 for t in proj['tasks'] if t['completed']) / len(proj['tasks']) if proj.get('tasks') else 0
        stat_txt = "DONE" if comp >= 1.0 else "ACTIVE"
        stat_col = "#10B981" if comp >= 1.0 else "#3B82F6"
        st.markdown(f'<div style="height: 28px;"></div>', unsafe_allow_html=True)
        st.markdown(f"<div class='pixel-status-badge' style='color:{stat_col}; border-color:{stat_col};'>{stat_txt}</div>", unsafe_allow_html=True)

    # --- DATES ---
    c3, c4 = st.columns(2)
    with c3:
        s_val = proj['start_date'].date() if isinstance(proj['start_date'], datetime) else proj['start_date']
        new_s = st.date_input("Start Date", value=s_val, key=f"d_start_{p_id}")
    with c4:
        e_val = proj['end_date'].date() if isinstance(proj['end_date'], datetime) else proj['end_date']
        new_e = st.date_input("Deadline", value=e_val, key=f"d_end_{p_id}")
    
    if new_s != s_val or new_e != e_val:
        proj['start_date'] = datetime.combine(new_s, datetime.min.time())
        proj['end_date'] = datetime.combine(new_e, datetime.min.time())
        save_data(st.session_state.projects)
        st.rerun()

    # --- REWARD ---
    curr_reward = proj.get('reward', '')
    new_reward = st.text_input("🎁 Reward", value=curr_reward, key=f"d_reward_{p_id}", placeholder="Reward for yourself...")
    if new_reward != curr_reward:
        proj['reward'] = new_reward
        save_data(st.session_state.projects)

    st.divider()
    
    # --- CHECKPOINTS ---
    st.markdown("<div style='font-family: VT323; font-size: 20px; color: #002FA7; margin-bottom: 10px;'>CHECKPOINTS</div>", unsafe_allow_html=True)
    
    if 'tasks' not in proj: proj['tasks'] = []
    
    for i, t in enumerate(proj['tasks']):
        c_k, c_n, c_d = st.columns([0.05, 0.85, 0.1])
        with c_k:
            is_done = st.checkbox("", value=t.get('completed', False), key=f"chk_{p_id}_{i}")
            if is_done != t.get('completed', False):
                t['completed'] = is_done
                save_data(st.session_state.projects)
                st.rerun()
        with c_n:
            task_name = t.get('task', t.get('name', 'Unnamed'))
            style = "color: #6E7280; text-decoration: line-through;" if t.get('completed', False) else "color: #002FA7;"
            st.markdown(f"<span style='{style} font-family: VT323; font-size: 18px;'>{task_name}</span>", unsafe_allow_html=True)
        with c_d:
            if st.button("x", key=f"rm_t_{p_id}_{i}"):
                proj['tasks'].pop(i)
                save_data(st.session_state.projects)
                st.rerun()
                
    new_task = st.text_input("New Checkpoint", placeholder="New task...", key=f"new_t_{p_id}", label_visibility="collapsed")
    if st.button("ADD", key=f"add_t_{p_id}", use_container_width=True) and new_task:
        proj['tasks'].append({"task": new_task, "completed": False})
        save_data(st.session_state.projects)
        st.rerun()

    st.markdown("---")

    # --- DELETE SECTION (Recycle Bin Icon) ---
    c_del_ico, c_del_btn = st.columns([0.2, 0.8])
    with c_del_ico:
        b64_img = get_img_b64(res_bin_path)
        if b64_img:
             st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{b64_img}" width="50"></div>', unsafe_allow_html=True)
        else:
             st.markdown("🗑️")

    with c_del_btn:
        st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)
        if st.button("THROW IN BIN", key=f"del_{p_id}", type="primary", use_container_width=True):
            st.session_state.projects = [x for x in st.session_state.projects if str(x.get('id')) != p_id_str]
            save_data(st.session_state.projects)
            st.rerun()

# --- Helper: List Popup (Charts) ---
@st.dialog("Project List")
def view_project_list_dialog(title, p_infos):
    st.caption(f"Showing: {title}")
    if not p_infos:
        st.info("No projects.")
        return
    
    for i, p in enumerate(p_infos):
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.write(f"**{p['Goal']}**")
            st.caption(f"{p['Start']} → {p['Deadline']} | {p['Status']}")
        with col2:
            if st.button("View", key=f"list_view_{p['_id']}_{i}"):
                st.session_state.pending_detail_id = p['_id']
                st.rerun()


def render_review_dashboard(projects):
    # FIX: Light Mode Compatible Buttons & CARD STYLE
    st.markdown("""
    <style>
        /* Review Dashboard Buttons - PIXEL ART STYLE */
        section[data-testid="stMain"] .stButton > button {
            background-color: #FFFFFF !important;
            color: #002FA7 !important;
            border: 2px solid #002FA7 !important;
            border-radius: 0px !important;
            box-shadow: 4px 4px 0px rgba(0,0,0,0.1) !important;
            font-family: 'VT323', monospace !important;
            font-size: 20px !important;
            font-weight: bold !important;
            transition: all 0.1s ease !important;
        }
        section[data-testid="stMain"] .stButton > button:hover {
            transform: translate(2px, 2px) !important;
            box-shadow: 2px 2px 0px rgba(0,0,0,0.1) !important;
            background-color: #F0F4F8 !important;
        }
        section[data-testid="stMain"] .stButton > button:active {
            transform: translate(4px, 4px) !important;
            box-shadow: none !important;
        }

        /* Download Button Fix */
        .stDownloadButton > button {
            background-color: #3B82F6 !important;
            color: #FFFFFF !important;
            border: 2px solid #002FA7 !important; /* Match border */
        }
        .stDownloadButton > button:hover {
            background-color: #2563EB !important;
        }

        /* TETRIS/VOXEL STYLE BUTTONS (Targeting Month Selection) */
        /* We use the specific key structure from Streamlit if possible, or general button override */
        /* Since we can't easily target by ID, we'll apply this style to ALL secondary buttons in this view */
        div[data-testid="stHorizontalBlock"] button {
            background-color: #E0E0E0 !important;
            color: #002FA7 !important;
            border: 2px solid #002FA7 !important;
            /* Tetra-style 3D Bevel on BOX only */
            box-shadow: inset 4px 4px 0px rgba(255, 255, 255, 0.9), inset -4px -4px 0px rgba(0, 0, 0, 0.2) !important;
            border-radius: 0px !important;
            font-family: 'VT323', monospace !important;
            font-weight: bold !important;
            /* Force Square */
            aspect-ratio: 1 / 1 !important;
            min-height: 50px !important;
            padding: 0px !important; 
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: normal !important;
            /* Remove text shadow */
            text-shadow: none !important;
            margin: 0 auto; /* Center in column */
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            background-color: #F9DC24 !important; /* Highlight Yellow */
            box-shadow: inset 4px 4px 0px rgba(255, 255, 255, 0.6), inset -4px -4px 0px rgba(0, 0, 0, 0.1) !important;
            color: #000 !important;
        }
        div[data-testid="stHorizontalBlock"] button:active {
            box-shadow: inset 3px 3px 0px rgba(0, 0, 0, 0.2), inset -3px -3px 0px rgba(255, 255, 255, 0.6) !important;
            transform: translate(2px, 2px);
        }
        


        /* PIXEL ART RADIO BUTTONS (SQUARE STYLE) */
        /* Target the Radio Button Outer Box */
        div[data-testid="stRadio"] label > div:first-child {
            background-color: #FFFFFF !important;
            border: 2px solid #002FA7 !important;
            border-radius: 0px !important; /* Make it square */
            width: 18px !important;
            height: 18px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: #FFFFFF !important;
        }

        /* Target the inner dot when selected */
        /* Using :has(input:checked) as found by inspection */
        div[data-testid="stRadio"] label:has(input:checked) > div:first-child {
            background-color: #002FA7 !important; /* Blue background when checked */
        }
        
        div[data-testid="stRadio"] label:has(input:checked) > div:first-child div {
            background-color: #F9DC24 !important; /* Yellow Pixel Dot */
            width: 8px !important;
            height: 8px !important;
            border-radius: 0px !important; /* Ensure it is a square */
            opacity: 1 !important;
        }

        /* Hide the default Streamlit marker div if it exists and is not our target */
        div[data-testid="stRadio"] label:not(:has(input:checked)) > div:first-child div {
            display: none !important;
        }


        /* PIXEL ART CONTAINER STYLE */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF;
            border: 2px solid #002FA7 !important; /* Dark Blue Border */
            box-shadow: 4px 4px 0px rgba(0,0,0,0.1); /* Pixel Shadow */
            padding: 20px;
            border-radius: 0px !important; /* Sharp corners */
            margin-bottom: 20px;
        }
        /* Remove inner gap if needed */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            gap: 1rem;
        }

        /* Module Headers -> MATCH TIME BANK STYLE */
        .review-card-header {
            background: #002FA7 !important;
            color: #F9DC24 !important;
            font-family: 'VT323', monospace;
            font-weight: bold;
            text-align: center;
            border: 2px solid #F9DC24 !important;
            padding: 4px 0;
            font-size: 24px;
            text-transform: uppercase;
            margin-bottom: 12px;
            box-shadow: 0px 4px 0px rgba(0,0,0,0.1);
            transform: rotate(-1deg); /* Slight stamp effect */
            display: block;
            width: 100%;
            letter-spacing: 1px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Custom Title -> MATCH CALENDAR TITLE STYLE (FEBRUARY 2026)
    st.markdown('''
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
        margin-bottom: 30px;
    ">
        REVIEW & RETROSPECT
    </div>
    ''', unsafe_allow_html=True)
    
    if not projects:
        st.info("No projects to review yet.")
        return

    today = datetime.now().date()
    
    # --- Handle Pending Detail ---
    if 'pending_detail_id' in st.session_state and st.session_state.pending_detail_id:
        detail_id = st.session_state.pending_detail_id
        st.session_state.pending_detail_id = None
        view_project_dialog(detail_id)

    # --- MODULE 1: YEARLY DENSITY ---
    with st.container(border=True):
        st.markdown('<div class="review-card-header">📅 Yearly Density</div>', unsafe_allow_html=True)
        
        start_year = today.replace(month=1, day=1)
        end_year = today.replace(month=12, day=31)
        year_projects = []
        for p in projects:
            s = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
            e = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
            if s <= end_year and e >= start_year:
                year_projects.append(p)

        month_counts = {m: 0 for m in range(1, 13)}
        for p in year_projects:
            s = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
            e = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
            for m in range(1, 13):
                if m == 12: ms, me = datetime(today.year, m, 1).date(), datetime(today.year, m, 31).date()
                else: ms, me = datetime(today.year, m, 1).date(), (datetime(today.year, m+1, 1) - timedelta(days=1)).date()
                if s <= me and e >= ms: month_counts[m] += 1

        # Mini Buttons for Months (Pixel Art Label)
        st.markdown('<div class="passbook-label" style="font-size: 16px; margin-bottom: 10px; color:#002FA7;">SELECT MONTH TO VIEW DETAILS (MONTH):</div>', unsafe_allow_html=True)
        
        month_cols = st.columns(12)
        clicked_month = None
        for i, m in enumerate(range(1, 13)):
            with month_cols[i]:
                label = datetime(today.year, m, 1).strftime("%b")
                count = month_counts[m]
                # Button style handled by Global CSS above
                if st.button(f"{count}", key=f"mo_{m}", help=f"{label}: {count} projects", type="secondary"):
                    clicked_month = m

        # Bar Chart (Visual - Pixel Art)
        df_year = pd.DataFrame([{"Month": datetime(today.year, m, 1).strftime("%b"), "Count": c} for m, c in month_counts.items()])
        fig_bar = px.bar(df_year, x="Month", y="Count", text="Count", title=None)
        fig_bar.update_layout(
            margin=dict(t=20, l=10, r=10, b=0), # Increased top margin for text clearance if outside
            xaxis=dict(
                showgrid=False, 
                showline=True, 
                linecolor='#002FA7', 
                linewidth=2,
                tickfont=dict(family='VT323, monospace', size=16, color='#002FA7')
            ), 
            xaxis_title=None, # REMOVED MONTH LABEL
            yaxis=dict(showgrid=False, showline=False, visible=False), 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(family='VT323, monospace', size=16, color='#002FA7'), 
            height=180 # Increased height for text
        )
        fig_bar.update_traces(
            textposition='inside',
            insidetextanchor='end', # Top of the bar
            textfont=dict(family='VT323, monospace', size=18, color='#002FA7'),
            marker_color='#00CC96', 
            marker_line_width=2, 
            marker_line_color='#002FA7',
            opacity=1.0
        )
        st.plotly_chart(fig_bar, use_container_width=True, key="chart_year_dense_visual")

        # Handle Month Click
        if clicked_month:
            m = clicked_month
            if m == 12: ms, me = datetime(today.year, m, 1).date(), datetime(today.year, m, 31).date()
            else: ms, me = datetime(today.year, m, 1).date(), (datetime(today.year, m+1, 1) - timedelta(days=1)).date()
            matches = []
            for p in year_projects:
                s = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
                e = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                if s <= me and e >= ms:
                    matches.append(p)
            p_infos = []
            for p in matches:
                comp = sum(1 for t in p['tasks'] if t['completed']) / len(p['tasks']) if p['tasks'] else 0
                p_stat = "Active"
                e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                if comp >= 1.0: p_stat = "Completed"
                elif today > e_date: p_stat = "Late"
                p_infos.append({
                    "Goal": p['goal'],
                    "Start": p['start_date'].strftime("%Y-%m-%d"),
                    "Deadline": p['end_date'].strftime("%Y-%m-%d"),
                    "Status": p_stat,
                    "_id": p.get('id')
                })
            view_project_list_dialog(f"{datetime(today.year, m, 1).strftime('%B')}", p_infos)


    # --- MODULE 2: KEY PERFORMANCE INDICATORS ---
    with st.container(border=True):
        st.markdown('<div class="review-card-header">📊 KPIs & Rhythm</div>', unsafe_allow_html=True)

        # --- Filter Section (Visual Row) ---
        # Adjusted ratio to force radio buttons on one line
        f_col1, f_col2 = st.columns([0.75, 0.25]) 
        with f_col1:
            period = st.radio("Time Period", ["Last 7 Days", "This Month", "This Year", "Custom Range"], horizontal=True, label_visibility="visible")
        with f_col2:
            custom_dates = []
            if period == "Custom Range":
                custom_dates = st.date_input("Select Date Range", value=[], help="Pick start and end dates")

        start_filter = None
        end_filter = datetime.max.date()
        prev_start_filter = None
        prev_end_filter = None
        prev_inclusive = False

        if period == "Custom Range":
            prev_inclusive = True
            if len(custom_dates) == 2:
                start_filter, end_filter = custom_dates[0], custom_dates[1]
                duration = end_filter - start_filter
                prev_end_filter = start_filter - timedelta(days=1)
                prev_start_filter = prev_end_filter - duration
            elif len(custom_dates) == 1:
                start_filter = end_filter = custom_dates[0]
            else:
                start_filter = end_filter = today
        elif period == "Last 7 Days":
            start_filter = today - timedelta(days=7)
            prev_start_filter = start_filter - timedelta(days=7)
            prev_end_filter = start_filter
        elif period == "This Month":
            start_filter = today.replace(day=1)
            first = today.replace(day=1)
            prev_end_filter = first
            prev_month = first - timedelta(days=1)
            prev_start_filter = prev_month.replace(day=1)
        elif period == "This Year":
            start_filter = today.replace(month=1, day=1)
            prev_end_filter = start_filter
            prev_start_filter = start_filter.replace(year=start_filter.year-1)

        current_projects = []
        prev_projects = []

        for p in projects:
            s_date = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
            if s_date >= start_filter and s_date <= end_filter:
                current_projects.append(p)
            if prev_start_filter and prev_end_filter:
                if prev_inclusive:
                    if s_date >= prev_start_filter and s_date <= prev_end_filter: prev_projects.append(p)
                else:
                    if s_date >= prev_start_filter and s_date < prev_end_filter: prev_projects.append(p)

        filtered = current_projects

        # --- Calculate Stats ---
        def calc_stats(projs):
            if not projs: return 0, 0, 0, 0, 0, 0
            cnt = len(projs)
            avg_prog = sum(sum(1 for t in p['tasks'] if t['completed'])/len(p['tasks']) if p['tasks'] else 0 for p in projs) / cnt
            on_time_cnt, early_cnt, late_cnt, total_delay = 0, 0, 0, 0
            for p in projs:
                comp = sum(1 for t in p['tasks'] if t['completed'])/len(p['tasks']) if p['tasks'] else 0
                e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                if comp >= 1.0:
                    c_at = p.get('completed_at')
                    is_early = False
                    if c_at:
                        try:
                            c_dt = datetime.fromisoformat(str(c_at)) if isinstance(c_at, str) else c_at
                            if c_dt.date() < e_date: is_early = True
                        except: pass
                    if is_early: early_cnt += 1
                    else: on_time_cnt += 1
                else:
                    if today > e_date:
                        late_cnt += 1
                        total_delay += (today - e_date).days
            return cnt, avg_prog, (early_cnt/cnt if cnt else 0), (on_time_cnt/cnt if cnt else 0), (late_cnt/cnt if cnt else 0), (total_delay/late_cnt if late_cnt else 0)

        curr_cnt, curr_prog, curr_early, curr_ot, curr_lr, curr_del = calc_stats(current_projects)
        prev_cnt, prev_prog, prev_early, prev_ot, prev_lr, prev_del = calc_stats(prev_projects)

            
        # Metrics Row
        def display_stat(col, label, value, delta_val, inverse=False):
            delta_color = "#9CA3AF" # Grey
            arrow = ""
            if delta_val != 0:
                if not inverse:
                    if delta_val > 0: delta_color, arrow = "#10B981", "↑"
                    else: delta_color, arrow = "#EF4444", "↓"
                else:
                    if delta_val > 0: delta_color, arrow = "#EF4444", "↑" # High delay is bad
                    else: delta_color, arrow = "#10B981", "↓" # Lower delay is good
            
            # FIXED: REMOVED BACKGROUND BOX, JUST TEXT
            col.markdown(f"""
                <div style="text-align: center; height: 120px; padding: 5px; border: 1px dashed #E0E0E0; border-radius: 4px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <div style="font-size: 0.9em; font-weight: bold; color: #002FA7; opacity: 0.8; margin-bottom: 2px; font-family: 'VT323', monospace; text-transform: uppercase;">{label}</div>
                    <div style="font-size: 2.2em; line-height: 1; font-weight: 700; color: #002FA7; margin: 4px 0; font-family: 'VT323', monospace;">{value}</div>
                    <div style="flex-grow: 1;"></div> 
                    <div style="font-size: 1.4em; color: {delta_color}; font-weight: bold; font-family: 'VT323', monospace; margin-top: 4px;">
                        {arrow} {abs(delta_val) if isinstance(delta_val, int) else delta_val}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        k1, k2, k3, k4, k5 = st.columns(5)
        display_stat(k1, "Projects", curr_cnt, curr_cnt - prev_cnt)
        
        prog_delta = int((curr_prog-prev_prog)*100)
        display_stat(k2, "Execution", f"{int(curr_prog*100)}%", prog_delta)
        
        early_delta = int((curr_early-prev_early)*100)
        display_stat(k3, "Early", f"{int(curr_early*100)}%", early_delta)
        
        ot_delta = int((curr_ot-prev_ot)*100)
        display_stat(k4, "On-Time", f"{int(curr_ot*100)}%", ot_delta)
        
        lr_delta = int((curr_lr-prev_lr)*100)
        display_stat(k5, "Delay Rate", f"{int(curr_lr*100)}%", lr_delta, inverse=True)

        # --- MOVED AI ANALYSIS HERE (NO HEADER, LARGER TEXT) ---
        st.markdown("---") # Divider

        # Planning Analysis Logic - REFACTORED TO MATCH TIME BANK SUGGESTIONS (CARD STYLE)
        # Unified Card Style for Rhythm & AI
        
        analysis_icon = "✅"
        analysis_title = "RHYTHM: BALANCED"
        analysis_desc = "Your completion rate is steady."
        analysis_tip = "Keep this pace."
        
        if curr_lr > 0.3:
            analysis_icon = "⚠️"
            analysis_title = "RHYTHM: LAG DETECTED"
            analysis_desc = f"Delay Rate is High ({int(curr_lr*100)}%)."
            analysis_tip = "Focus on clearing backlog."
        elif curr_early > 0.3:
            analysis_icon = "🌊" 
            analysis_title = "RHYTHM: ACCELERATED"
            analysis_desc = f"Early Completion Rate is High ({int(curr_early*100)}%)."
            analysis_tip = "Consider increasing load."

        # RENDER RHYTHM INDICATOR (SAME STYLE AS AI SUGGESTIONS)
        st.markdown(f"""
        <div class="passbook-container" style="margin-bottom: 20px; background: #F8FAFC; border: 1px dashed #B0C4DE; padding: 12px; border-radius: 8px;">
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 1.4rem;">{analysis_icon}</div>
                <div>
                    <div style="font-weight: 700; color: #1E3A8A; margin-bottom: 6px; font-size: 1.1em;">{analysis_title}</div>
                    <div style="font-size: 1.05rem; color: #334155; margin-bottom: 10px; line-height: 1.5;">{analysis_desc}</div>
                    <div style="font-size: 0.95rem; background: #FEF3C7; color: #92400E; padding: 4px 8px; border-radius: 4px; display: inline-block; font-weight: 600;">
                        TIP: {analysis_tip}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
            
        patterns = analyze_patterns(projects)
        suggestions = generate_suggestions(patterns)
        
        if not suggestions:
            st.info("No patterns detected yet.")
        else:
            for s in suggestions:
                if isinstance(s, dict):
                    # INCREASED FONT SIZE
                    st.markdown(f"""
                    <div class="passbook-container" style="margin-bottom: 10px; background: #F8FAFC; border: 1px dashed #B0C4DE; padding: 12px; border-radius: 8px;">
                        <div style="display: flex; align-items: flex-start; gap: 12px;">
                            <div style="font-size: 1.4rem;">💡</div>
                            <div>
                                <div style="font-weight: 700; color: #1E3A8A; margin-bottom: 6px; font-size: 1.1em;">{s.get('title', '')}</div>
                                <div style="font-size: 1.05rem; color: #334155; margin-bottom: 10px; line-height: 1.5;">{s.get('description', '')}</div>
                                <div style="font-size: 0.95rem; background: #FEF3C7; color: #92400E; padding: 4px 8px; border-radius: 4px; display: inline-block; font-weight: 600;">
                                    TIP: {s.get('tip', '')}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


    # --- MODULE 3: PROJECT LIST ---
    with st.container(border=True):
        st.markdown('<div class="review-card-header">📋 Project Drill-down</div>', unsafe_allow_html=True)
        
        tab_list, tab_time = st.tabs(["📋 List View", "⏳ Time Machine"])
        
        with tab_list:
            if filtered:
                # Iterate and display projects
                for i, p in enumerate(filtered):
                    comp = sum(1 for t in p['tasks'] if t['completed']) / len(p['tasks']) if p['tasks'] else 0
                    p_status = "Active"
                    e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                    if comp >= 1.0: p_status = "Completed"
                    elif today > e_date: p_status = "Late"
                    
                    mood = p.get('completion_mood', '')
                    title_display = f"{mood} {p['goal']}" if mood else p['goal']
                    
                    # Status Color Logic
                    status_color = "#3B82F6" # Active Blue
                    if p_status == "Completed": status_color = "#10B981" # Green
                    elif p_status == "Late": status_color = "#EF4444" # Red
                    
                    # Tags Rendering
                    tags_html = ""
                    if p.get('tags'):
                        for t in p['tags']:
                            tags_html += f'<span style="background: #EBF8FF; color: #3182CE; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-right: 4px;">#{t}</span>'

                    col1, col2 = st.columns([0.85, 0.15])
                    with col1:
                        # Centered Title & Status Row within a fixed-ish height container
                        st.markdown(f"""
                        <div style="border-bottom: 1px solid #E2E8F0; padding: 12px 0; min-height: 70px; display: flex; flex-direction: column; justify-content: center;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-weight: 600; color: #1E293B; font-size: 1.1em; line-height: 1.2;">{title_display}</span>
                                <span style="background:{status_color}; color:white; padding:2px 8px; border-radius:12px; font-size: 0.75em; font-weight: bold;">{p_status.upper()}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>{tags_html}</div>
                                <div style="font-size: 0.85em; color: #64748B;">Deadline: {e_date}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with col2:
                        # Reverting to simple top alignment for button (user preferred previous style)
                        st.write(" ") # Tiny spacer
                        if st.button("View", key=f"drill_view_{p.get('id', i)}", use_container_width=True):
                            st.session_state.pending_detail_id = p.get('id')
                            st.rerun()
            else:
                st.info("No projects match the filter.")

        with tab_time:
            # VERSION MARKER (Vertical Redesign)
            st.caption("Time Machine Engine v5.1 (Vertical Mode)")
            
            if filtered:
                # Sort projects by start date for timeline
                sorted_projs = sorted(filtered, key=lambda x: x['start_date'])
                
                # Calculate relative positions based on vertical height
                start_all = min(p['start_date'] for p in sorted_projs)
                end_all = max(p['end_date'] for p in sorted_projs)
                total_days = (end_all - start_all).days or 1
                
                nodes_list = []
                for i, p in enumerate(sorted_projs):
                    days_from_start = (p['start_date'] - start_all).days
                    top_offset = days_from_start * 25 # Increased spacing
                    
                    comp = sum(1 for t in p['tasks'] if t['completed']) / len(p['tasks']) if p['tasks'] else 0
                    p_status_cls = "active"
                    e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                    if comp >= 1.0: p_status_cls = "completed"
                    elif today > e_date: p_status_cls = "late"
                    
                    # Horizontal zig-zag offset
                    h_offset = (i % 2) * 20
                    
                    # SINGLE LINE HTML to prevent markdown rendering bugs
                    node_html = f'<div class="tm-v51-node {p_status_cls}" style="top: {top_offset}px;"></div>'
                    content_html = f'<div class="tm-v51-content" style="top: {top_offset - 10}px; left: {40 + h_offset}px;"><span class="tm-v51-date">{p["start_date"].strftime("%b %d")}</span><span class="tm-v51-goal">{p["goal"][:25]}...</span></div>'
                    nodes_list.append(node_html + content_html)

                nodes_combined = "".join(nodes_list)
                container_height = max(total_days * 25 + 100, 400)

                st.markdown(textwrap.dedent(f"""
                <style>
                .tm-v51-wrapper {{
                    background: #F8FAFC;
                    border: 4px solid #002FA7;
                    border-radius: 8px;
                    padding: 40px;
                    image-rendering: pixelated;
                    max-height: 700px;
                    overflow-y: auto;
                    position: relative;
                }}
                .tm-v51-container {{
                    position: relative;
                    height: {container_height}px;
                    padding-left: 50px;
                }}
                .tm-v51-axis {{
                    position: absolute;
                    left: 20px;
                    top: 0;
                    bottom: 0;
                    width: 8px;
                    background: #002FA7;
                    z-index: 1;
                }}
                .tm-v51-axis::after {{
                    content: "";
                    position: absolute;
                    top: 0; bottom: 0; left: 2px;
                    width: 4px;
                    background: #F9DC24;
                }}
                .tm-v51-node {{
                    position: absolute;
                    left: 16px;
                    width: 16px;
                    height: 16px;
                    background: #FFF;
                    border: 3px solid #002FA7;
                    transform: translateY(-50%);
                    z-index: 2;
                }}
                .tm-v51-node.completed {{ background: #10B981; }}
                .tm-v51-node.late {{ background: #EF4444; }}
                .tm-v51-node.active {{ background: #3B82F6; }}
                
                .tm-v51-content {{
                    position: absolute;
                    display: flex;
                    flex-direction: column;
                    font-family: 'VT323', monospace;
                    background: white;
                    border: 2px solid #002FA7;
                    padding: 6px 10px;
                    box-shadow: 4px 4px 0px rgba(0, 47, 167, 0.2);
                    min-width: 180px;
                }}
                .tm-v51-date {{
                    font-size: 11px;
                    color: #64748B;
                    border-bottom: 1px solid #EEE;
                    margin-bottom: 2px;
                }}
                .tm-v51-goal {{
                    font-size: 14px;
                    color: #002FA7;
                    font-weight: bold;
                }}
                </style>
                <div class="tm-v51-wrapper">
                    <div class="tm-v51-container">
                        <div class="tm-v51-axis"></div>
                        {nodes_combined}
                    </div>
                </div>
                """), unsafe_allow_html=True)
            else:
                st.info("No projects to map in Time Machine.")

    # --- MODULE 4: CHARTS (Full Width Status Bar) ---
    with st.container(border=True):
        st.markdown('<div class="review-card-header">📉 Status Breakdown</div>', unsafe_allow_html=True)
            
        if filtered:
            early, on_time, late, active = 0, 0, 0, 0
            status_map = {}
            for p in filtered:
                comp_val = sum(1 for t in p['tasks'] if t['completed'])/len(p['tasks']) if p['tasks'] else 0
                p_stat = "Active"
                if comp_val >= 1.0:
                    c_at = p.get('completed_at')
                    is_e = False
                    if c_at:
                        try:
                            c_dt = datetime.fromisoformat(str(c_at)) if isinstance(c_at, str) else c_at
                            if c_dt.date() < (p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']): is_e = True
                        except: pass
                    if is_e: p_stat = "Early"; early+=1
                    else: p_stat = "On Time"; on_time+=1
                elif today > (p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']):
                    p_stat = "Late"; late+=1
                else: active +=1
                status_map[p.get('id')] = p_stat

            # Custom Horizontal Pixel Bar
            total = early + on_time + late + active
            total = total if total > 0 else 1 # Avoid division by zero
            p_early = (early / total) * 100
            p_ontime = (on_time / total) * 100
            p_late = (late / total) * 100
            p_active = (active / total) * 100
            
            st.markdown(f"""
            <div style="margin: 20px 0;">
                <div style="display: flex; height: 30px; border: 2px solid #002FA7; border-radius: 4px; overflow: hidden; background: #EEE; image-rendering: pixelated;">
                    <div style="width: {p_early}%; background: #10B981; border-right: 1px solid #002FA7;" title="Early: {early}"></div>
                    <div style="width: {p_ontime}%; background: #3B82F6; border-right: 1px solid #002FA7;" title="On Time: {on_time}"></div>
                    <div style="width: {p_late}%; background: #EF4444; border-right: 1px solid #002FA7;" title="Late: {late}"></div>
                    <div style="width: {p_active}%; background: #A855F7;" title="Active: {active}"></div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 10px; font-family: 'VT323', monospace; font-size: 14px; color: #002FA7;">
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#10B981;"></div> Early ({early})</div>
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#3B82F6;"></div> On Time ({on_time})</div>
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#EF4444;"></div> Late ({late})</div>
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#A855F7;"></div> Active ({active})</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- Report Section (Always Expanded) ---
            st.markdown('<div class="review-card-header">📥 Export & Report</div>', unsafe_allow_html=True)
            report_tabs = st.tabs(["Weekly", "Monthly", "Yearly"])
            
            # Common Report Data Preparation
            report_data = []
            completed_count = 0
            for p in filtered:
                total_tasks = len(p['tasks'])
                done_tasks = sum(1 for t in p['tasks'] if t['completed'])
                completion = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
                p_stat_rep = status_map.get(p.get('id'), "Active")
                if completion >= 100: completed_count += 1
                
                s_date = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
                e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                
                # Time Status
                if p_stat_rep == "Late":
                    days_diff = (today - e_date).days
                    time_status = f"Overdue {days_diff}d"
                elif p_stat_rep in ["Early", "On Time"]:
                    time_status = "Done"
                else:
                    days_diff = (e_date - today).days
                    time_status = f"{days_diff}d left"
                
                report_data.append({
                    "Goal": p['goal'],
                    "Start Date": s_date.strftime("%Y-%m-%d"),
                    "Deadline": e_date.strftime("%Y-%m-%d"),
                    "Status": p_stat_rep,
                    "Time Status": time_status
                })
            
            df_report = pd.DataFrame(report_data)
            csv = df_report.to_csv(index=False).encode('utf-8')

            with report_tabs[0]: # Weekly
                # Generate Text Report (Weekly)
                week_start = today - timedelta(days=today.weekday())
                week_end = week_start + timedelta(days=6)
                st.markdown(f"""
                <div style="background: white; border: 2px solid #002FA7; padding: 24px; border-radius: 8px; box-shadow: 6px 6px 0px rgba(0, 47, 167, 0.1); margin: 10px 0;">
                    <div style="font-size: 1.4rem; font-weight: 800; color: #002FA7; margin-bottom: 8px; font-family: 'VT323', monospace;">📊 WEEKLY REPORT SUMMARY</div>
                    <div style="font-size: 1.25rem; color: #475569; font-weight: 600; font-family: 'VT323', monospace; margin-bottom: 12px;">📅 {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}</div>
                    <div style="font-size: 2.8rem; color: #10B981; font-weight: 900; line-height: 1; font-family: 'VT323', monospace;">✅ {completed_count}/{len(filtered)} DONE</div>
                </div>
                """, unsafe_allow_html=True)
                st.download_button("Download Weekly CSV", csv, f"weekly_report.csv", "text/csv", key="dl_weekly", use_container_width=True)

            with report_tabs[1]: # Monthly
                st.markdown(f"""
                <div style="background: white; border: 2px solid #002FA7; padding: 24px; border-radius: 8px; box-shadow: 6px 6px 0px rgba(0, 47, 167, 0.1); margin: 10px 0;">
                    <div style="font-size: 1.4rem; font-weight: 800; color: #002FA7; margin-bottom: 8px; font-family: 'VT323', monospace;">📊 MONTHLY PERFORMANCE</div>
                    <div style="font-size: 1.25rem; color: #475569; font-weight: 600; font-family: 'VT323', monospace; margin-bottom: 12px;">📅 {today.strftime('%B %Y')}</div>
                    <div style="font-size: 2.8rem; color: #10B981; font-weight: 900; line-height: 1; font-family: 'VT323', monospace;">✅ {completed_count}/{len(filtered)} DONE</div>
                </div>
                """, unsafe_allow_html=True)
                st.download_button("Download Monthly CSV", csv, f"monthly_report.csv", "text/csv", key="dl_monthly", use_container_width=True)

            with report_tabs[2]: # Yearly
                st.markdown(f"""
                <div style="background: white; border: 2px solid #002FA7; padding: 24px; border-radius: 8px; box-shadow: 6px 6px 0px rgba(0, 47, 167, 0.1); margin: 10px 0;">
                    <div style="font-size: 1.4rem; font-weight: 800; color: #002FA7; margin-bottom: 8px; font-family: 'VT323', monospace;">📊 YEAR-TO-DATE STATUS</div>
                    <div style="font-size: 1.25rem; color: #475569; font-weight: 600; font-family: 'VT323', monospace; margin-bottom: 12px;">📅 Year {today.year}</div>
                    <div style="font-size: 2.8rem; color: #10B981; font-weight: 900; line-height: 1; font-family: 'VT323', monospace;">✅ {completed_count}/{len(filtered)} DONE</div>
                </div>
                """, unsafe_allow_html=True)
                st.download_button("Download Yearly CSV", csv, f"yearly_report.csv", "text/csv", key="dl_yearly", use_container_width=True)

        else:
            st.info("No data.")