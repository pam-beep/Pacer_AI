
# --- Logic: Review Dashboard ---
def render_review_dashboard(projects):
    # 1. Top Section: Notepad & Priorities
    c1, c2 = st.columns([0.6, 0.4])
    
    with c1:
        with st.container(border=True):
            st.markdown('<div class="passbook-header">DAILY NOTEPAD</div>', unsafe_allow_html=True)
            if 'review_note' not in st.session_state: st.session_state.review_note = ""
            val = st.text_area("Journal", value=st.session_state.review_note, height=200, 
                               placeholder="Log your thoughts, energy levels, and wins...", label_visibility="collapsed")
            if val != st.session_state.review_note:
                st.session_state.review_note = val
    
    with c2:
        with st.container(border=True):
            st.markdown('<div class="passbook-header">TOMORROW\'s JUMP LIST</div>', unsafe_allow_html=True)
            if 'prio_1' not in st.session_state: st.session_state.prio_1 = ""
            if 'prio_2' not in st.session_state: st.session_state.prio_2 = ""
            if 'prio_3' not in st.session_state: st.session_state.prio_3 = ""
            
            st.session_state.prio_1 = st.text_input("1.", st.session_state.prio_1, placeholder="Must Do")
            st.session_state.prio_2 = st.text_input("2.", st.session_state.prio_2, placeholder="Should Do")
            st.session_state.prio_3 = st.text_input("3.", st.session_state.prio_3, placeholder="Could Do")
            
    # 2. Project Cards (Passbook Style)
    st.divider()
    st.markdown("### 🗂 Active Missions")
    
    active = [p for p in projects if calculate_completion(p['tasks']) < 1.0]
    if not active:
        st.info("No active missions. Good job!")
    
    cols = st.columns(3)
    for i, p in enumerate(active):
        with cols[i % 3]:
            # Use container with border (Passbook Style due to CSS)
            with st.container(border=True):
                # Header
                st.markdown(f'<div class="passbook-header" style="font-size:0.8em;">{p["goal"]}</div>', unsafe_allow_html=True)
                
                # Stats
                tasks_total = len(p['tasks'])
                tasks_done = sum(1 for t in p['tasks'] if t['completed'])
                pct = calculate_completion(p['tasks'])
                
                st.caption(f"Progress: {tasks_done}/{tasks_total}")
                st.progress(pct)
                
                # Deadline
                end_d = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
                days = (end_d - datetime.now().date()).days
                
                if days < 0:
                    st.markdown(f"<span style='color:red; font-weight:bold;'>Overdue by {abs(days)} days</span>", unsafe_allow_html=True)
                else:
                    st.caption(f"Due in {days} days")
                
                if st.button("Open", key=f"rev_open_{p['id']}", use_container_width=True):
                    st.session_state.selected_project_id = p['id']
                    st.session_state.view_mode = "Calendar" # Switch to main view to show dialog
                    st.rerun()

