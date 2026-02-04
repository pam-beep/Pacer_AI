import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from persistence import save_data
import uuid

# FIX: Light Mode Compatible Buttons for Review Dashboard
st.markdown("""
<style>
    /* Review Dashboard Buttons - Light Mode Fix */
    .stButton > button {
        background-color: #00CC96 !important;
        color: #FFFFFF !important;
        border: 1px solid #00AA7D !important;
        font-weight: 600 !important;
        min-width: 40px !important;
    }
    .stButton > button:hover {
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
    proj_ref = next((x for x in st.session_state.projects if str(x.get('id')) == p_id_str), None)
    if not proj_ref:
        st.error(f"Project not found. ID: {p_id}")
        return

    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        new_goal = st.text_input("Goal", value=proj_ref['goal'], key=f"d_goal_{p_id}")
        if new_goal != proj_ref['goal']:
            proj_ref['goal'] = new_goal
            save_data(st.session_state.projects)
            st.rerun()
    with c2:
        if st.button("🗑️", key=f"del_{p_id}", help="Delete Project"):
            st.session_state.projects = [x for x in st.session_state.projects if str(x.get('id')) != p_id_str]
            save_data(st.session_state.projects)
            st.rerun()

    c3, c4, c5 = st.columns([0.4, 0.4, 0.2])
    with c3:
        s_val = proj_ref['start_date'].date() if isinstance(proj_ref['start_date'], datetime) else proj_ref['start_date']
        new_s = st.date_input("Start Date", value=s_val, key=f"d_start_{p_id}")
    with c4:
        e_val = proj_ref['end_date'].date() if isinstance(proj_ref['end_date'], datetime) else proj_ref['end_date']
        new_e = st.date_input("Deadline", value=e_val, key=f"d_end_{p_id}")
    with c5:
        total_t = len(proj_ref['tasks'])
        done_t = sum(1 for t in proj_ref['tasks'] if t['completed'])
        pct = int((done_t / total_t * 100)) if total_t > 0 else 0
        st.metric("Progress", f"{pct}%")

    if new_s != s_val or new_e != e_val:
        proj_ref['start_date'] = datetime.combine(new_s, datetime.min.time())
        proj_ref['end_date'] = datetime.combine(new_e, datetime.min.time())
        save_data(st.session_state.projects)
        st.rerun()

    st.divider()
    st.subheader("Checklist")
    if 'tasks' not in proj_ref: proj_ref['tasks'] = []
    for i, t in enumerate(proj_ref['tasks']):
        c_k, c_n, c_d = st.columns([0.05, 0.85, 0.1])
        with c_k:
            is_done = st.checkbox("", value=t.get('completed', False), key=f"chk_{p_id}_{i}")
            if is_done != t.get('completed', False):
                t['completed'] = is_done
                save_data(st.session_state.projects)
                st.rerun()
        with c_n:
            task_name = t.get('task', t.get('name', 'Unnamed'))
            if t.get('completed', False):
                st.write(f"~~{task_name}~~")
            else:
                st.write(task_name)
        with c_d:
            if st.button("x", key=f"rm_t_{p_id}_{i}"):
                proj_ref['tasks'].pop(i)
                save_data(st.session_state.projects)
                st.rerun()
    new_task = st.text_input("Add Task", placeholder="New task...", key=f"new_t_{p_id}")
    if st.button("Add", key=f"add_t_{p_id}") and new_task:
        proj_ref['tasks'].append({"task": new_task, "completed": False})
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
    # FIX: Light Mode Compatible Buttons
    st.markdown("""
    <style>
        /* Review Dashboard Buttons - Light Mode Fix */
        .stButton > button {
            background-color: #00CC96 !important;
            color: #FFFFFF !important;
            border: 1px solid #00AA7D !important;
            font-weight: 600 !important;
        }
        .stButton > button:hover {
            background-color: #00AA7D !important;
        }
        /* Download Button Fix */
        .stDownloadButton > button {
            background-color: #3B82F6 !important;
            color: #FFFFFF !important;
            border: none !important;
        }
        .stDownloadButton > button:hover {
            background-color: #2563EB !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Review & Retrospect")
    if not projects:
        st.info("No projects to review yet.")
        return

    today = datetime.now().date()
    
    # --- Handle Pending Detail from List Popup ---
    if 'pending_detail_id' in st.session_state and st.session_state.pending_detail_id:
        detail_id = st.session_state.pending_detail_id
        st.session_state.pending_detail_id = None
        view_project_dialog(detail_id)

    # --- 1. Yearly Density (Global Context) ---
    st.subheader(f"📅 Yearly Density ({today.year})")

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

    # Mini Buttons for Months
    st.caption("Click month:")
    month_cols = st.columns(12)
    clicked_month = None
    for i, m in enumerate(range(1, 13)):
        with month_cols[i]:
            label = datetime(today.year, m, 1).strftime("%b")
            count = month_counts[m]
            if st.button(f"{count}", key=f"mo_{m}", help=f"{label}: {count} projects", type="primary"):
                clicked_month = m

    # Bar Chart (Visual)
    df_year = pd.DataFrame([{"Month": datetime(today.year, m, 1).strftime("%b"), "Count": c} for m, c in month_counts.items()])
    fig_bar = px.bar(df_year, x="Month", y="Count", title=None)
    fig_bar.update_layout(margin=dict(t=10, l=10, r=10, b=0), xaxis_title=None, yaxis_title=None, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#FAFAFA'), height=120)
    fig_bar.update_traces(marker_color='#00CC96')
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

    st.divider()

    # --- Filter Section ---
    with st.expander("Filter Data (Affects KPIs & Export)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            period = st.selectbox("Time Period", ["Last 7 Days", "This Month", "This Year", "Custom Range"])
        with c2:
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

    # --- KPIs ---
    st.subheader("Key Performance Indicators")
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
                        c_dt = datetime.fromisoformat(c_at) if isinstance(c_at, str) else c_at
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

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Projects", curr_cnt, delta=curr_cnt - prev_cnt)
    k2.metric("Execution", f"{int(curr_prog*100)}%", delta=f"{int((curr_prog-prev_prog)*100)}%")
    k3.metric("Early", f"{int(curr_early*100)}%", delta=f"{int((curr_early-prev_early)*100)}%")
    k4.metric("On-Time", f"{int(curr_ot*100)}%", delta=f"{int((curr_ot-prev_ot)*100)}%")
    k5.metric("Delay Rate", f"{int(curr_lr*100)}%", delta=f"{int((curr_lr-prev_lr)*100)}%", delta_color="inverse")

    st.caption("💡 **Planning Analysis**")
    if curr_lr > 0.3:
        st.warning(f"⚠️ High Delay Rate ({int(curr_lr*100)}%).")
    elif curr_early > 0.3:
        st.success(f"🚀 High Early Rate ({int(curr_early*100)}%)!")
    else:
        st.success(f"✅ Balanced. On-Time/Early: {int((curr_ot+curr_early)*100)}%.")

    st.divider()

    con_drill_visual = st.container()
    st.divider()
    con_bottom_visual = st.container()

    # --- Bottom Visuals ---
    with con_bottom_visual:
        c_status, c_export = st.columns([1, 1])
        with c_status:
            st.subheader("📊 Status Distribution")
            if filtered:
                early, on_time, late, active = 0, 0, 0, 0
                status_map = {}
                for p in filtered:
                    comp = sum(1 for t in p['tasks'] if t['completed'])/len(p['tasks']) if p['tasks'] else 0
                    p_stat = "Active"
                    if comp >= 1.0:
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

                labels = ["Early", "On Time", "Late", "Active"]
                values = [early, on_time, late, active]

                # Mini Status Buttons
                st.caption("Click status:")
                status_cols = st.columns(4)
                clicked_status = None
                for i, lbl in enumerate(labels):
                    with status_cols[i]:
                        if st.button(f"{values[i]}", key=f"st_{lbl}", help=f"{lbl}: {values[i]}", type="primary"):
                            clicked_status = lbl

                # Pie Chart
                fig_pie = px.pie(names=labels, values=values, hole=0.0)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    margin=dict(t=10,l=10,r=10,b=20),
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#FAFAFA'),
                    height=200
                )
                st.plotly_chart(fig_pie, use_container_width=True, key="chart_status_pie_visual")

                # Handle Status Click
                if clicked_status:
                    matches = []
                    for p in filtered:
                        if status_map.get(p.get('id')) == clicked_status:
                            matches.append({
                                "Goal": p['goal'],
                                "Start": p['start_date'].strftime("%Y-%m-%d"),
                                "Deadline": p['end_date'].strftime("%Y-%m-%d"),
                                "Status": clicked_status,
                                "_id": p.get('id')
                            })
                    view_project_list_dialog(f"{clicked_status}", matches)
            else:
                st.info("No projects in filter period.")

        with c_export:
            st.subheader("📤 Export Report Data")
            
            # Prepare Clean Report Data for CSV
            if filtered:
                report_data = []
                for p in filtered:
                    total_tasks = len(p['tasks'])
                    done_tasks = sum(1 for t in p['tasks'] if t['completed'])
                    completion = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
                    
                    # Calculate Status
                    p_stat = "Active"
                    s_date = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
                    e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                    duration = (e_date - s_date).days
                    
                    if completion >= 100:
                        c_at = p.get('completed_at')
                        is_e = False
                        if c_at:
                            try:
                                c_dt = datetime.fromisoformat(str(c_at)) if isinstance(c_at, str) else c_at
                                if c_dt.date() < e_date: is_e = True
                            except: pass
                        if is_e: p_stat = "Early"
                        else: p_stat = "On Time"
                    elif today > e_date:
                        p_stat = "Late"
                    
                    # Days Remaining or Overdue
                    if p_stat == "Late":
                        days_diff = (today - e_date).days
                        time_status = f"Overdue {days_diff}d"
                    elif p_stat in ["Early", "On Time"]:
                        time_status = "Done"
                    else:
                        days_diff = (e_date - today).days
                        time_status = f"{days_diff}d left"
                    
                    report_data.append({
                        "Goal": p['goal'],
                        "Start Date": s_date.strftime("%Y-%m-%d"),
                        "Deadline": e_date.strftime("%Y-%m-%d"),
                        "Duration (days)": duration,
                        "Tasks Total": total_tasks,
                        "Tasks Done": done_tasks,
                        "Completion %": f"{int(completion)}%",
                        "Status": p_stat,
                        "Time Status": time_status
                    })
                
                df_report = pd.DataFrame(report_data)
                
                # Summary Stats for Report Header
                st.caption(f"**Period**: {period}")
                st.caption(f"**Projects**: {len(filtered)} | **Avg Completion**: {int(curr_prog*100)}%")
                
                csv = df_report.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, f"pacer_report_{period.lower().replace(' ', '_')}.csv", "text/csv")
                
                # Preview
                with st.expander("Preview Data"):
                    st.dataframe(df_report, use_container_width=True, hide_index=True)
            else:
                st.info("No data to export.")

    # --- 3. Drill Down List (Using View Buttons) ---
    with con_drill_visual:
        st.subheader("📋 Project Drill-down")

        if filtered:
            for i, p in enumerate(filtered):
                comp = sum(1 for t in p['tasks'] if t['completed']) / len(p['tasks']) if p['tasks'] else 0
                p_status = "Active"
                e_date = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                if comp >= 1.0: p_status = "Completed"
                elif today > e_date: p_status = "Late"
                
                col1, col2, col3 = st.columns([0.6, 0.25, 0.15])
                with col1:
                    st.write(f"**{p['goal']}**")
                with col2:
                    st.caption(f"{p['start_date'].strftime('%m/%d')} → {p['end_date'].strftime('%m/%d')} | {int(comp*100)}% | {p_status}")
                with col3:
                    if st.button("View", key=f"drill_view_{p.get('id')}"):
                        view_project_dialog(p.get('id'))
        else:
            st.caption("No projects available.")