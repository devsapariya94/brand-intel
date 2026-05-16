"""Date and number formatting utilities"""
from datetime import datetime


def format_datetime(dt_str: str) -> str:
    """Format datetime string to readable format"""
    if not dt_str:
        return "N/A"
    try:
        if isinstance(dt_str, datetime):
            dt = dt_str
        else:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt_str)


def format_relative_time(dt_str: str) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')"""
    if not dt_str:
        return "Never"
    try:
        if isinstance(dt_str, datetime):
            dt = dt_str
        else:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        else:
            return f"{seconds // 86400}d ago"
    except Exception:
        return str(dt_str)


def format_number(num: int) -> str:
    """Format large numbers with K/M suffix"""
    if num is None:
        return "0"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def format_percentage(value: float) -> str:
    """Format as percentage"""
    return f"{value * 100:.1f}%"
