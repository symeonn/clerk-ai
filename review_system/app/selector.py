"""Reminder selection logic."""

from typing import List, Dict, Any
from datetime import datetime


def select_top_reminders(
    review_items: List[Dict[str, Any]],
    next_actions: List[Dict[str, Any]],
    max_count: int = 3
) -> List[Dict[str, Any]]:
    """
    Select top reminders from combined list.
    
    Priority:
        1. Explicit next actions (from project anchors)
        2. Recently modified items
        3. Items not completed
    
    Args:
        review_items: Items from 01_review/
        next_actions: Next actions from project anchors
        max_count: Maximum number of reminders to return (default: 3)
    
    Returns:
        List of selected reminders, up to max_count items
    """
    # Combine all candidates
    candidates = []
    
    # Add next actions with higher priority
    for action in next_actions:
        candidates.append({
            **action,
            "priority": 1,  # Highest priority
            "display": f"[[{action['path']}|{action['project']}]] {action['action']}"
        })
    
    # Add review items with lower priority
    for item in review_items:
        candidates.append({
            **item,
            "priority": 2,  # Lower priority
            "display": f"Review: {item['title']}"
        })
    
    # Sort by priority (ascending), then by modified date (descending)
    candidates.sort(
        key=lambda x: (x["priority"], -x["modified"].timestamp())
    )
    
    # Return top N
    return candidates[:max_count]
