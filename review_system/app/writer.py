"""Daily note writer."""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


def write_daily_note(
    vault_path: str,
    reminders: List[Dict[str, Any]],
    date: Optional[datetime] = None
) -> str:
    """
    Create or overwrite today's daily note with selected reminders and project links.
    
    Args:
        vault_path: Path to vault root
        reminders: List of selected reminders
        date: Date for the daily note (default: today)
    
    Returns:
        Path to created daily note
    """
    if date is None:
        date = datetime.now()
    
    # Format: YYYY-MM-DD.md
    # filename = date.strftime("%Y-%m-%d.md")
    filename = "TODAY.md"
    daily_note_path = Path(vault_path) / filename
    
    # Build content
    content_lines = []
    
    # Add reminders section
    if reminders:
        for reminder in reminders:
            content_lines.append(f"- {reminder['display']}")
    else:
        content_lines.append("- No reminders for today")
    
    # Add projects section
    projects_dir = Path(vault_path) / "10_projects"
    if projects_dir.exists():
        content_lines.append("")
        content_lines.append("## Projects")
        
        # Get all .md files in 10_projects root (not in subfolders)
        project_files = sorted([f for f in projects_dir.glob("*.md") if f.is_file()])
        
        for project_file in project_files:
            project_name = project_file.stem
            # Create Obsidian link: [[10_projects/project_name]]
            content_lines.append(f"- [[10_projects/{project_name}|{project_name}]]")
    
    content = "\n".join(content_lines) + "\n"
    
    # Write to file (overwrite if exists)
    daily_note_path.write_text(content, encoding="utf-8")
    
    return str(daily_note_path)
