import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from persistence import save_data, load_journal, save_journal, load_focus_data
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

# --- REMOVED REDUNDANT DIALOG (Moved to app.py for unification) ---

# --- Helper: List Popup (Charts) ---
@st.dialog("PROJECT LIST")
def view_project_list_dialog(title, p_infos):
    st.markdown("""
    <style>
    div[data-testid="stDialog"] div[data-testid="stDialogHeader"] { display: none !important; }
    button[aria-label="Close"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    # Header Row
    c_h1, c_h2 = st.columns([0.88, 0.12])
    with c_h1:
        st.markdown(f"<div style='font-family: VT323; font-size: 24px; color: #002FA7; font-weight: bold; text-transform: uppercase;'>PROJECT LIST: {title}</div>", unsafe_allow_html=True)
    with c_h2:
        if st.button("❌", key="close_list_dialog"):
            st.rerun()
            
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
                st.session_state.selected_project_id = p['_id']
                st.rerun()


def render_review_dashboard(projects):
    # Redirect pending details to the master selected_project_id
    if st.session_state.get('pending_detail_id'):
        st.session_state.selected_project_id = st.session_state.pending_detail_id
        st.session_state.pending_detail_id = None
        st.rerun()

    today = datetime.now().date()
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

        /* Module Headers (Big Headers) -> RESTORED PIXEL ART STYLE */
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
            transform: rotate(-1deg);
            display: block;
            width: 100%;
            letter-spacing: 1px;
        }

        /* Secondary Headers (Tabs: List View, Time Machine, Weekly, Monthly, Yearly) -> MATCH RHYTHM STYLE */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
        }
        button[data-baseweb="tab"] div p,
        button[data-baseweb="tab"] span,
        button[data-baseweb="tab"] div {
            font-weight: 700 !important;
            color: #1E3A8A !important;
            font-size: 1.1em !important;
            font-family: inherit !important;
        }
        /* Active Tab Highlight */
        button[data-baseweb="tab"][aria-selected="true"] {
             border-bottom-color: #002FA7 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] div p {
             color: #002FA7 !important;
        }

        /* METRIC LABELS (Early, On Time, etc.) */
        div[data-testid="stMetricLabel"] p {
            font-weight: 700 !important;
            color: #1E3A8A !important;
            font-size: 1.1em !important;
        }

        /* WIDGET LABELS (Time Period, Making Progress) */
        div[data-testid="stWidgetLabel"] p,
        div[data-testid="stWidgetLabel"] label {
            font-weight: 700 !important;
            color: #1E3A8A !important;
            font-size: 1.1em !important;
        }

        /* CUSTOM SUB-HEADER CLASS -> MATCH RHYTHM STYLE */
        .rhythm-sub-header {
            font-weight: 700 !important;
            color: #1E3A8A !important;
            font-size: 1.1em !important;
            margin-bottom: 8px;
            display: block;
            text-transform: none;
            font-family: inherit;
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
    # Unified dispatcher in app.py handles selected_project_id
    if 'pending_detail_id' in st.session_state and st.session_state.pending_detail_id:
        st.session_state.selected_project_id = st.session_state.pending_detail_id
        st.session_state.pending_detail_id = None
        st.rerun()

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
            # Only count in the Start Month to avoid duplicate counting across months
            if s.year == today.year:
                month_counts[s.month] += 1

        # Mini Buttons for Months (Pixel Art Label)
        st.markdown('<div class="rhythm-sub-header">Select Month to View Details (Month):</div>', unsafe_allow_html=True)
        
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


        # --- POMODORO FOCUS STATISTICS ---
        st.markdown("---")
        st.markdown('<div class="rhythm-sub-header">Pomodoro Focus Time Statistics (Minutes):</div>', unsafe_allow_html=True)
        
        # FOCUS STATS: Pull from session state first
        focus_data = st.session_state.get('focus_sessions', load_focus_data())
        focus_month_counts = {m: 0 for m in range(1, 13)}
        
        for sess in focus_data:
            s_date = sess.get('date')
            if s_date:
                if isinstance(s_date, str):
                    try:
                        s_date = datetime.fromisoformat(s_date)
                    except: continue
                if s_date.year == today.year:
                    m = s_date.month
                    focus_month_counts[m] += sess.get('duration', 0)
        
        # Focus Bar Chart
        df_focus = pd.DataFrame([{"Month": datetime(today.year, m, 1).strftime("%b"), "Minutes": c} for m, c in focus_month_counts.items()])
        fig_focus = px.bar(df_focus, x="Month", y="Minutes", text="Minutes", title=None)
        fig_focus.update_layout(
            margin=dict(t=20, l=10, r=10, b=0),
            xaxis=dict(
                showgrid=False, 
                showline=True, 
                linecolor='#002FA7', 
                linewidth=2,
                tickfont=dict(family='VT323, monospace', size=16, color='#002FA7')
            ), 
            xaxis_title=None,
            yaxis=dict(showgrid=False, showline=False, visible=False), 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(family='VT323, monospace', size=16, color='#002FA7'), 
            height=180
        )
        fig_focus.update_traces(
            textposition='inside',
            insidetextanchor='end',
            textfont=dict(family='VT323, monospace', size=18, color='#002FA7'),
            marker_color='#F9DC24',  # Yellow for Focus
            marker_line_width=2, 
            marker_line_color='#002FA7',
            opacity=1.0
        )
        st.plotly_chart(fig_focus, use_container_width=True, key="chart_focus_year")


    # --- MODULE 2: KEY PERFORMANCE INDICATORS ---
    with st.container(border=True):
        st.markdown('<div class="review-card-header">📊 KPIs & Rhythm</div>', unsafe_allow_html=True)

        # --- Filter Section (Visual Row) ---
        # Adjusted ratio to force radio buttons on one line
        f_col1, f_col2 = st.columns([0.75, 0.25]) 
        with f_col1:
            st.markdown('<div class="rhythm-sub-header">Time Period</div>', unsafe_allow_html=True)
            period = st.radio("Time Period", ["Last 7 Days", "This Month", "This Year", "Custom Range"], horizontal=True, label_visibility="collapsed")
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
            s_val = p.get('start_date')
            if isinstance(s_val, str):
                try: s_date = datetime.fromisoformat(s_val).date()
                except: s_date = datetime.max.date()
            elif isinstance(s_val, datetime):
                s_date = s_val.date()
            else:
                s_date = s_val

            e_val = p.get('end_date')
            if isinstance(e_val, str):
                try: e_date = datetime.fromisoformat(e_val).date()
                except: e_date = datetime.max.date()
            elif isinstance(e_val, datetime):
                e_date = e_val.date()
            else:
                e_date = e_val
            
            # Use Overlap Logic: Project Start <= Filter End AND Project End >= Filter Start
            if s_date <= end_filter and e_date >= start_filter:
                current_projects.append(p)
                
            if prev_start_filter and prev_end_filter:
                # Comparison logic for previous period (also overlap)
                if prev_inclusive:
                    if s_date <= prev_end_filter and e_date >= prev_start_filter: prev_projects.append(p)
                else:
                    if s_date < prev_end_filter and e_date >= prev_start_filter: prev_projects.append(p)

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
        analysis_title = "Rhythm: Balanced"
        analysis_desc = "Your completion rate is steady."
        analysis_tip = "Keep this pace."
        
        if curr_lr > 0.3:
            analysis_icon = "⚠️"
            analysis_title = "Rhythm: Lag Detected"
            analysis_desc = f"Delay Rate is High ({int(curr_lr*100)}%)."
            analysis_tip = "Focus on clearing backlog."
        elif curr_early > 0.3:
            analysis_icon = "🌊" 
            analysis_title = "Rhythm: Accelerated"
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
                            st.session_state.selected_project_id = p.get('id')
                            st.rerun()
            else:
                st.info("No projects match the filter.")

        with tab_time:
            # VERSION MARKER (Vertical Redesign)
            # VERSION MARKER (Vertical Redesign) - Removed caption
            
            # TIME MACHINE: Always show all projects from the current year for a complete timeline
            tm_projects = [p for p in projects if p['start_date'].year == today.year]
            if tm_projects:
                # REDESIGNED TIME MACHINE: Unique Dates & Stacked Projects
                sorted_projs = sorted(tm_projects, key=lambda x: x['start_date'])
                
                # Group by date
                from collections import defaultdict
                date_groups = defaultdict(list)
                for p in sorted_projs:
                    d_str = p['start_date'].strftime("%Y-%m-%d")
                    date_groups[d_str].append(p)
                
                sorted_dates = sorted(date_groups.keys())
                
                nodes_list = []
                current_top = 20
                
                for d_str in sorted_dates:
                    projs_on_day = date_groups[d_str]
                    dt = datetime.fromisoformat(d_str).date()
                    
                    # Date Node
                    node_html = f'<div class="tm-v51-node" style="top: {current_top}px;"></div>'
                    date_html = f'<div class="tm-v51-date-left" style="top: {current_top - 10}px;">{dt.strftime("%b %d")}</div>'
                    nodes_list.append(node_html + date_html)
                    
                    # Projects on this day (Stacked)
                    for j, p in enumerate(projs_on_day):
                        comp = sum(1 for t in p['tasks'] if t['completed']) / len(p['tasks']) if p['tasks'] else 0
                        st_cls = "active"
                        e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                        if comp >= 1.0: st_cls = "completed"
                        elif today > e_date: st_cls = "late"
                        
                        # Stack offset
                        stack_h = j * 45 # Increased for full text
                        stack_l = j * 15 # Stacked effect
                        
                        p_html = f'''
                        <div class="tm-v51-goal-right {st_cls}" style="top: {current_top - 10 + stack_h}px; left: {110 + stack_l}px; z-index: {100-j};">
                            <span class="tm-v51-goal">{p["goal"]}</span>
                        </div>
                        '''
                        nodes_list.append(p_html)
                    
                    # Increment current_top for next date group
                    current_top += max(len(projs_on_day) * 50, 70)
                
                nodes_combined = "".join(nodes_list)
                container_height = max(current_top + 100, 500)

                # Robust HTML Construction
                tm_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
                <style>
                body {{
                    margin: 0; padding: 0;
                    background-color: transparent;
                    font-family: 'VT323', monospace;
                }}
                .tm-v51-wrapper {{
                    background: #F8FAFC;
                    border: 4px solid #002FA7;
                    border-radius: 8px;
                    padding: 40px;
                    min-height: {container_height}px; 
                    position: relative;
                    box-sizing: border-box;
                }}
                .tm-v51-container {{
                    position: relative;
                    height: {container_height}px;
                    padding-left: 80px;
                }}
                .tm-v51-axis {{
                    position: absolute;
                    left: 80px;
                    top: 0; bottom: 0;
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
                    left: 76px;
                    width: 16px; height: 16px;
                    background: #FFF;
                    border: 3px solid #002FA7;
                    transform: translateY(-50%);
                    z-index: 2;
                }}
                .tm-v51-date-left {{
                    position: absolute;
                    right: calc(100% - 75px);
                    font-size: 16px;
                    color: #002FA7;
                    font-weight: bold;
                    text-align: right;
                    width: 70px;
                }}
                .tm-v51-goal-right {{
                    position: absolute;
                    display: flex;
                    flex-direction: column;
                    background: white;
                    border: 2px solid #002FA7;
                    padding: 8px 14px;
                    box-shadow: 4px 4px 0px rgba(0, 47, 167, 0.1);
                    min-width: 280px;
                    max-width: 450px;
                }}
                .tm-v51-goal-right.completed {{ border-left: 8px solid #10B981; }}
                .tm-v51-goal-right.late {{ border-left: 8px solid #EF4444; }}
                .tm-v51-goal-right.active {{ border-left: 8px solid #3B82F6; }}
                
                .tm-v51-goal {{
                    font-size: 18px;
                    color: #002FA7;
                    font-weight: bold;
                    white-space: normal;
                    line-height: 1.2;
                }}
                </style>
                </head>
                <body>
                    <div class="tm-v51-wrapper">
                        <div class="tm-v51-container">
                            <div class="tm-v51-axis"></div>
                            {nodes_combined}
                        </div>
                    </div>
                </body>
                </html>
                """
                import streamlit.components.v1 as components
                components.html(tm_html, height=550, scrolling=True)
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
                <div style="display: flex; justify-content: space-between; margin-top: 10px; color: #1E3A8A; font-weight: 700; font-size: 1em;">
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#10B981;"></div> Early ({early})</div>
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#3B82F6;"></div> On Time ({on_time})</div>
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#EF4444;"></div> Late ({late})</div>
                    <div style="display: flex; align-items: center; gap: 4px;"><div style="width:10px; height:10px; background:#A855F7;"></div> Active ({active})</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- Report Section (Unified by selection) ---
            st.markdown('<div class="review-card-header">📥 Export & Report</div>', unsafe_allow_html=True)
            
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
            df_report = pd.DataFrame(report_data)
            # UTF-8 with BOM for Excel compatibility
            csv = df_report.to_csv(index=False).encode('utf-8-sig')

            st.markdown(f"""
            <div style="background: white; border: 2px solid #002FA7; padding: 24px; border-radius: 8px; box-shadow: 6px 6px 0px rgba(0, 47, 167, 0.1); margin: 10px 0;">
                <div style="font-size: 1.4rem; font-weight: 800; color: #002FA7; margin-bottom: 8px; font-family: 'VT323', monospace;">📊 EXPORT REPORT SUMMARY</div>
                <div style="font-size: 1.25rem; color: #475569; font-weight: 600; font-family: 'VT323', monospace; margin-bottom: 12px;">📅 SELECTED PERIOD: {period.upper()}</div>
                <div style="font-size: 2.8rem; color: #10B981; font-weight: 900; line-height: 1; font-family: 'VT323', monospace;">✅ {completed_count}/{len(filtered)} DONE</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.download_button("Download Data (CSV for Excel)", csv, f"report_{period.lower().replace(' ','_')}.csv", "text/csv", key="dl_report", use_container_width=True)
        else:
            st.info("No data.")