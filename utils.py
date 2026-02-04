from datetime import datetime, timedelta
import re
import dateparser
import os
from openai import OpenAI

# Mock AI / Fallback with Context Awareness
def mock_generate_tasks(goal):
    goal_lower = goal.lower()
    
    # 1. Travel / Trip
    if any(k in goal_lower for k in ["travel", "trip", "visit", "flight", "hotel", "旅行", "出差", "订票"]):
        return [
            {"task": "Book flights and accommodation", "completed": False},
            {"task": "Pack luggage and essentials", "completed": False},
            {"task": "Check execution plan / itinerary", "completed": False},
            {"task": "Confirm travel documents (ID/Passport)", "completed": False},
        ]
        
    # 2. Study / Learning / Reading
    if any(k in goal_lower for k in ["study", "learn", "read", "course", "exam", "学习", "阅读", "考试", "看书"]):
        return [
            {"task": "Define learning objectives", "completed": False},
            {"task": "Gather study materials/books", "completed": False},
            {"task": "Daily study session (Morning)", "completed": False},
            {"task": "Review and summarize notes", "completed": False},
        ]
        
    # 3. Work / Project / Coding
    if any(k in goal_lower for k in ["code", "dev", "project", "meeting", "report", "工作", "代码", "项目", "会议"]):
        return [
            {"task": "Outline project requirements", "completed": False},
            {"task": "Draft initial implementation", "completed": False},
            {"task": "Review and refine", "completed": False},
            {"task": "Final submission/deployment", "completed": False},
        ]
    
    # 4. Health / Fitness
    if any(k in goal_lower for k in ["gym", "run", "workout", "diet", "健身", "跑步", "运动"]):
        return [
            {"task": "Prepare gear/equipment", "completed": False},
            {"task": "Warm up exercise", "completed": False},
            {"task": "Main workout session", "completed": False},
            {"task": "Cool down and stretch", "completed": False},
        ]

    # Default Generic
    return [
        {"task": f"Research info for {goal}", "completed": False},
        {"task": f"Draft Plan for {goal}", "completed": False},
        {"task": f"Execute {goal}", "completed": False},
        {"task": f"Review outcome", "completed": False},
    ]

def generate_checklist(user_input):
    """
    Parses natural language input to extract project dates and tasks.
    Returns: (tasks_list, start_date, end_date)
    """
    
    # 1. Date Parsing
    
    today = datetime.now()
    start_date = today
    end_date = today + timedelta(days=7) # Default one week
    
    # Simple Date Parser Helper
    def parse_smart_date(text):
        # A. Chinese Range: 2月1日-2月19日 or 2月1日到2月19日
        # Pattern: (\d+)月(\d+)日\s*[-到]\s*(\d+)月(\d+)日
        match_cn_range = re.search(r'(\d+)月(\d+)日\s*[-到]\s*(\d+)月(\d+)日', text)
        if match_cn_range:
            try:
                m1, d1, m2, d2 = map(int, match_cn_range.groups())
                s = today.replace(month=m1, day=d1)
                e = today.replace(month=m2, day=d2)
                if s < today - timedelta(days=300): s = s.replace(year=s.year+1)
                if e < s: e = e.replace(year=e.year+1)
                return s, e, True
            except: pass

        # B. Chinese Single Date: 2月1日
        match_cn_single = re.search(r'(\d+)月(\d+)日', text)
        if match_cn_single:
            try:
                m1, d1 = map(int, match_cn_single.groups())
                s = today.replace(month=m1, day=d1)
                if s < today - timedelta(days=300): s = s.replace(year=s.year+1)
                return s, s, True # Start = End
            except: pass

        # C. Slash Format Range: M/D-M/D
        match_range = re.search(r'(\d{1,2})[/-](\d{1,2})\s*-\s*(\d{1,2})[/-](\d{1,2})', text)
        if match_range:
            try:
                m1, d1, m2, d2 = map(int, match_range.groups())
                s = today.replace(month=m1, day=d1)
                e = today.replace(month=m2, day=d2)
                if s < today - timedelta(days=300): s = s.replace(year=s.year+1)
                if e < s: e = e.replace(year=e.year+1)
                return s, e, True
            except: pass
            
        # D. Slash Format Simple Range: M/D-D
        match_days = re.search(r'(\d{1,2})[/-](\d{1,2})\s*-\s*(\d{1,2})', text)
        if match_days:
            try:
                m1, d1, d2 = map(int, match_days.groups())
                s = today.replace(month=m1, day=d1)
                e = today.replace(month=m1, day=d2)
                if s < today - timedelta(days=300): s = s.replace(year=s.year+1)
                if e < s: e = e.replace(year=e.year+1)
                return s, e, True
            except: pass
            
        return start_date, end_date, False

    s, e, found = parse_smart_date(user_input)
    if found:
        start_date, end_date = s, e
    else:
        # Fallback to dateparser for "Next Friday", "Feb 8" etc
        # dateparser typically handles "2月1日" too, but regex is faster/explicit
        try:
             # languages=['en', 'zh'] ensures Chinese support
             dates = dateparser.search.search_dates(user_input, languages=['en', 'zh'], settings={'PREFER_DATES_FROM': 'future'})
             if dates:
                 # dates is list of (text, date_obj)
                 start_date = dates[0][1]
                 if len(dates) > 1:
                     end_date = dates[1][1]
                 else:
                     end_date = start_date
        except:
            pass

    # Ensure start <= end
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # 2. AI Task Generation
    api_key = os.getenv("OPENAI_API_KEY")
    tasks = []
    
    # Try AI but fall back to smart template if it fails or if key missing
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            # More specific prompt for context
            prompt = f"Identify the type of project (e.g., Travel, Work, Study) from: '{user_input}'. Then generate a checklist of 4 concrete, short steps for it. Return only the steps as a bulleted list."
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            content = response.choices[0].message.content
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('* ') or (line[0].isdigit() and line[1] == '.'):
                    task_txt = re.sub(r'^[-*\d\.]+\s*', '', line)
                    if task_txt:
                        tasks.append({"task": task_txt, "completed": False})
        except Exception as e:
            print(f"AI Error: {e}")
            tasks = mock_generate_tasks(user_input)
    
    if not tasks:
        tasks = mock_generate_tasks(user_input)
        
    return tasks, start_date, end_date
