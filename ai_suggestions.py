# AI Smart Suggestions Module
# Analyzes project history to detect procrastination patterns and provide personalized tips

from datetime import datetime, timedelta

def analyze_patterns(projects):
    """
    Analyze project history to detect procrastination patterns.
    Returns a list of detected pattern objects with type and details.
    """
    if not projects:
        return []
    
    patterns = []
    
    # Filter completed projects for analysis
    completed = []
    late_projects = []
    
    today = datetime.now().date()
    
    for p in projects:
        tasks = p.get('tasks', [])
        if not tasks:
            continue
        
        completion = sum(1 for t in tasks if t.get('completed', False)) / len(tasks)
        
        start_d = p['start_date'].date() if isinstance(p['start_date'], datetime) else p['start_date']
        end_d = p['end_date'].date() if isinstance(p['end_date'], datetime) else p['end_date']
        
        if completion >= 1.0:
            completed.append({
                'project': p,
                'start': start_d,
                'end': end_d,
                'duration': (end_d - start_d).days + 1,
                'completion': completion
            })
        elif today > end_d:
            late_projects.append({
                'project': p,
                'start': start_d,
                'end': end_d,
                'duration': (end_d - start_d).days + 1,
                'delay': (today - end_d).days,
                'completion': completion
            })
    
    # Pattern 1: Weekend Procrastinator
    # Check if most delays correlate with weekend start dates
    weekend_delays = 0
    weekday_delays = 0
    for lp in late_projects:
        if lp['start'].weekday() >= 5:  # Saturday=5, Sunday=6
            weekend_delays += 1
        else:
            weekday_delays += 1
    
    if len(late_projects) >= 3 and weekend_delays > weekday_delays:
        patterns.append({
            'type': 'weekend_procrastinator',
            'title': '📅 Weekend Procrastinator',
            'description': f'You have {weekend_delays} delayed projects started on weekends.',
            'tip': 'Try starting important projects on Monday mornings when energy is fresh.'
        })
    
    # Pattern 2: Long Project Avoider
    # Check if longer projects have lower completion rates
    long_projects = [p for p in late_projects if p['duration'] > 14]
    short_projects = [p for p in completed if p['duration'] <= 7]
    
    if len(long_projects) >= 2 and len(short_projects) >= 2:
        long_avg_comp = sum(p['completion'] for p in long_projects) / len(long_projects) if long_projects else 1.0
        short_avg_comp = sum(p['completion'] for p in short_projects) / len(short_projects) if short_projects else 0
        
        if long_avg_comp < 0.5 and short_avg_comp > 0.8:
            patterns.append({
                'type': 'long_project_avoider',
                'title': '📏 Big Project Aversion',
                'description': f'Long projects (>2 weeks) have {int(long_avg_comp*100)}% avg completion vs {int(short_avg_comp*100)}% for short ones.',
                'tip': 'Break large projects into smaller 1-week milestones.'
            })
    
    # Pattern 3: Deadline Sprinter
    # Check if tasks are completed close to deadline (would need task timestamps - simplified version)
    if len(late_projects) >= 2:
        avg_delay = sum(p['delay'] for p in late_projects) / len(late_projects)
        if avg_delay > 3:
            patterns.append({
                'type': 'deadline_sprinter',
                'title': '🏃 Deadline Sprinter',
                'description': f'Your late projects average {int(avg_delay)} days overdue.',
                'tip': 'Set personal deadlines 2-3 days before actual deadlines.'
            })
    
    # Pattern 4: High Performer (Positive!) - More lenient
    if len(completed) >= 2 and len(late_projects) == 0:
        patterns.append({
            'type': 'high_performer',
            'title': '🌟 Rhythm Master',
            'description': f'Excellent! {len(completed)} projects completed on time.',
            'tip': 'Keep up the great work! Consider setting more ambitious goals.'
        })
    elif len(completed) >= 1 and len(late_projects) <= 1:
        on_time_rate = len(completed) / (len(completed) + len(late_projects)) * 100 if (len(completed) + len(late_projects)) > 0 else 100
        patterns.append({
            'type': 'good_progress',
            'title': '👍 Making Progress',
            'description': f'{int(on_time_rate)}% on-time completion rate.',
            'tip': 'You\'re building good habits. Keep the momentum!'
        })
    
    # Pattern 5: Getting Started (New User)
    if len(projects) <= 3:
        patterns.append({
            'type': 'new_user',
            'title': '🚀 Just Getting Started',
            'description': 'Welcome! Add more projects to unlock deeper insights.',
            'tip': 'Try adding 3-5 projects to see pattern analysis.'
        })
    
    # Default: If still no patterns, add a general encouraging message
    if not patterns:
        total_projects = len(projects)
        active_count = total_projects - len(completed) - len(late_projects)
        if active_count > 0:
            patterns.append({
                'type': 'keep_going',
                'title': '💪 Keep Going',
                'description': f'You have {active_count} active projects in progress.',
                'tip': 'Focus on completing one project at a time for best results.'
            })
        else:
            patterns.append({
                'type': 'ready_to_start',
                'title': '🎯 Ready for Action',
                'description': 'Your slate is clean! Time to plan new goals.',
                'tip': 'Set a new project with a realistic deadline to get started.'
            })
    
    return patterns


def generate_suggestions(patterns):
    """
    Convert detected patterns into actionable suggestions.
    Returns a list of suggestion strings.
    """
    if not patterns:
        return ["✨ No patterns detected yet. Keep tracking your projects!"]
    
    suggestions = []
    for p in patterns:
        suggestions.append({
            'title': p['title'],
            'description': p['description'],
            'tip': p['tip']
        })
    
    return suggestions
