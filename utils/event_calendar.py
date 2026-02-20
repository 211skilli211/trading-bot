#!/usr/bin/env python3
"""
Macro Event Calendar
====================
Tracks high-impact macro events that can cause volatility spikes.

Pauses trading before/after major events to avoid getting stopped out.

Events tracked:
- FOMC meetings and rate decisions
- NFP (Non-Farm Payrolls)
- CPI/PCE inflation data
- Fed Chair speeches
- US Elections
- Tax deadlines
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# High-impact macro events calendar
# Format: date (YYYY-MM-DD), event name, pause window, impact level
MACRO_EVENTS: List[Dict] = [
    # February 2026
    {"date": "2026-02-20", "time": "17:30", "event": "PCE Inflation Data", "pause_minutes": 30, "impact": "HIGH"},
    {"date": "2026-02-26", "time": "19:00", "event": "Fed Minutes", "pause_minutes": 60, "impact": "HIGH"},
    
    # March 2026
    {"date": "2026-03-07", "time": "13:30", "event": "NFP Report", "pause_minutes": 30, "impact": "HIGH"},
    {"date": "2026-03-19", "time": "18:00", "event": "FOMC Rate Decision", "pause_minutes": 90, "impact": "CRITICAL"},
    {"date": "2026-03-26", "time": "19:00", "event": "Fed Chair Powell Speech", "pause_minutes": 60, "impact": "HIGH"},
    
    # April 2026 (Tax Season)
    {"date": "2026-04-15", "event": "US Tax Deadline", "pause_hours": 24, "impact": "MEDIUM"},
    {"date": "2026-04-29", "time": "13:30", "event": "GDP Q1 Advance", "pause_minutes": 30, "impact": "HIGH"},
    
    # May 2026
    {"date": "2026-05-02", "time": "13:30", "event": "NFP Report", "pause_minutes": 30, "impact": "HIGH"},
    {"date": "2026-05-07", "time": "18:00", "event": "FOMC Rate Decision", "pause_minutes": 90, "impact": "CRITICAL"},
    {"date": "2026-05-15", "time": "17:30", "event": "PCE Inflation Data", "pause_minutes": 30, "impact": "HIGH"},
    
    # June 2026
    {"date": "2026-06-06", "time": "13:30", "event": "NFP Report", "pause_minutes": 30, "impact": "HIGH"},
    {"date": "2026-06-18", "time": "18:00", "event": "FOMC Rate Decision", "pause_minutes": 90, "impact": "CRITICAL"},
    
    # July 2026
    {"date": "2026-07-04", "event": "US Holiday (July 4)", "pause_hours": 12, "impact": "LOW"},
    {"date": "2026-07-11", "time": "13:30", "event": "NFP Report", "pause_minutes": 30, "impact": "HIGH"},
    {"date": "2026-07-29", "time": "18:00", "event": "FOMC Rate Decision", "pause_minutes": 90, "impact": "CRITICAL"},
    
    # September 2026 (Quarterly OpEx)
    {"date": "2026-09-18", "event": "Quarterly Options Expiry", "pause_hours": 6, "impact": "MEDIUM"},
    
    # October 2026 (Start of Q4)
    {"date": "2026-10-02", "time": "13:30", "event": "NFP Report", "pause_minutes": 30, "impact": "HIGH"},
    {"date": "2026-10-29", "time": "18:00", "event": "FOMC Rate Decision", "pause_minutes": 90, "impact": "CRITICAL"},
    
    # November 2026 (Elections - CRITICAL)
    {"date": "2026-11-03", "event": "US Midterm Elections", "pause_hours": 48, "impact": "CRITICAL"},
    {"date": "2026-11-06", "time": "13:30", "event": "NFP Report", "pause_minutes": 30, "impact": "HIGH"},
    
    # December 2026 (Year-end)
    {"date": "2026-12-16", "time": "18:00", "event": "FOMC Rate Decision", "pause_minutes": 90, "impact": "CRITICAL"},
    {"date": "2026-12-25", "event": "Christmas Holiday", "pause_hours": 24, "impact": "LOW"},
    {"date": "2026-12-31", "event": "New Year (Year-end flows)", "pause_hours": 12, "impact": "MEDIUM"},
]


def should_pause_trading(now: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    Check if trading should pause due to upcoming or ongoing macro event.
    
    Args:
        now: Optional datetime to check (defaults to current time)
        
    Returns:
        (should_pause, reason)
    """
    if now is None:
        now = datetime.now()
    
    for event in MACRO_EVENTS:
        event_date = datetime.strptime(event['date'], '%Y-%m-%d')
        
        # Handle events with specific times
        if 'time' in event:
            event_time = datetime.strptime(
                f"{event['date']} {event['time']}", 
                '%Y-%m-%d %H:%M'
            )
            pause_window = timedelta(minutes=event.get('pause_minutes', 30))
            
            # Check if we're in the pause window
            if event_time - pause_window <= now <= event_time + pause_window:
                reason = f"Macro event: {event['event']} ({event['impact']}) - "
                if now < event_time:
                    mins_until = int((event_time - now).total_seconds() / 60)
                    reason += f"starts in {mins_until}m"
                else:
                    mins_since = int((now - event_time).total_seconds() / 60)
                    reason += f"started {mins_since}m ago"
                return True, reason
        
        # Handle all-day events
        elif 'pause_hours' in event:
            event_window = timedelta(hours=event['pause_hours'])
            start_time = datetime.combine(event_date.date(), datetime.min.time())
            
            if start_time - event_window <= now <= start_time + event_window:
                reason = f"Macro event: {event['event']} ({event['impact']})"
                return True, reason
    
    return False, ""


def get_upcoming_events(days: int = 7, now: Optional[datetime] = None) -> List[Dict]:
    """
    Get macro events for next N days.
    
    Args:
        days: Number of days to look ahead
        now: Optional datetime (defaults to current time)
        
    Returns:
        List of upcoming events
    """
    if now is None:
        now = datetime.now()
    
    upcoming = []
    
    for event in MACRO_EVENTS:
        event_date = datetime.strptime(event['date'], '%Y-%m-%d')
        
        if now <= event_date <= now + timedelta(days=days):
            # Calculate time until event
            days_until = (event_date - now).days
            hours_until = int((event_date - now).total_seconds() / 3600)
            
            upcoming.append({
                **event,
                'days_until': days_until,
                'hours_until': hours_until
            })
    
    # Sort by date
    upcoming.sort(key=lambda x: x['date'])
    return upcoming


def get_next_critical_event(now: Optional[datetime] = None) -> Optional[Dict]:
    """
    Get the next CRITICAL impact event.
    
    Args:
        now: Optional datetime (defaults to current time)
        
    Returns:
        Next critical event or None
    """
    upcoming = get_upcoming_events(days=365, now=now)
    
    for event in upcoming:
        if event.get('impact') == 'CRITICAL':
            return event
    
    return None


def time_until_next_event(now: Optional[datetime] = None) -> Optional[int]:
    """
    Get hours until next macro event of any impact.
    
    Args:
        now: Optional datetime (defaults to current time)
        
    Returns:
        Hours until next event, or None if no events
    """
    upcoming = get_upcoming_events(days=365, now=now)
    
    if upcoming:
        return upcoming[0].get('hours_until')
    
    return None


class MacroCalendar:
    """
    Macro event calendar manager.
    
    Usage:
        calendar = MacroCalendar()
        if calendar.should_pause():
            # Don't trade
        upcoming = calendar.get_upcoming(days=7)
    """
    
    def __init__(self):
        self.events = MACRO_EVENTS
        logger.info(f"[MacroCalendar] Loaded {len(self.events)} macro events")
    
    def should_pause(self) -> Tuple[bool, str]:
        """Check if trading should pause"""
        return should_pause_trading()
    
    def get_upcoming(self, days: int = 7) -> List[Dict]:
        """Get upcoming events"""
        return get_upcoming_events(days)
    
    def get_next_critical(self) -> Optional[Dict]:
        """Get next critical event"""
        return get_next_critical_event()
    
    def is_event_day(self) -> bool:
        """Check if today has any macro events"""
        today = datetime.now().strftime('%Y-%m-%d')
        return any(e['date'] == today for e in self.events)


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("MACRO EVENT CALENDAR TEST")
    print("=" * 60)
    
    # Check if should pause
    should_pause, reason = should_pause_trading()
    print(f"\nShould Pause Trading: {'YES' if should_pause else 'NO'}")
    if should_pause:
        print(f"Reason: {reason}")
    
    # Get upcoming events
    print("\nUpcoming Events (Next 30 days):")
    print("-" * 60)
    upcoming = get_upcoming_events(days=30)
    for event in upcoming[:5]:
        time_info = f"at {event['time']}" if 'time' in event else "(all day)"
        print(f"  {event['date']} {time_info}")
        print(f"    {event['event']} [{event['impact']}]")
        print(f"    In {event['days_until']} days ({event['hours_until']} hours)")
        print()
    
    # Next critical event
    critical = get_next_critical_event()
    if critical:
        print(f"Next CRITICAL Event: {critical['event']} on {critical['date']}")
    
    print("=" * 60)
