"""Vault scanning logic for review items and project next actions."""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import re


def scan_review_folder(vault_path: str) -> List[Dict[str, Any]]:
    """
    Scan 01_review/ folder for notes requiring attention.
    
    Returns list of dicts with:
        - path: relative path to note
        - title: note title/filename
        - modified: last modified timestamp
    """
    review_path = Path(vault_path) / "01_review"
    items = []
    
    if not review_path.exists():
        return items
    
    for file_path in review_path.glob("*.md"):
        if file_path.is_file():
            stat = file_path.stat()
            items.append({
                "path": str(file_path.relative_to(vault_path)),
                "title": file_path.stem,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "type": "review"
            })
    
    return items


def scan_projects_for_next_actions(vault_path: str) -> List[Dict[str, Any]]:
    """
    Scan 10_projects/ for anchor files and extract next actions.
    
    Looks for:
        - Anchor files (project_name.md in 10_projects/)
        - Sections like "## Next Actions", "## TODO", "## Next Steps"
        - Bullet points under those sections
    
    Returns list of dicts with:
        - path: path to anchor file
        - project: project name
        - action: extracted action text
        - modified: last modified timestamp
    """
    projects_path = Path(vault_path) / "10_projects"
    actions = []
    
    if not projects_path.exists():
        return actions
    # Find anchor files (markdown files directly in 10_projects/)
    for anchor_file in projects_path.glob("*.md"):
        if anchor_file.is_file():
            print(f"Found anchor file: {anchor_file}")

            project_name = anchor_file.stem
            stat = anchor_file.stat()
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            # Parse anchor file for next actions
            extracted_actions = _extract_next_actions(anchor_file)
            
            for action_text in extracted_actions:
                actions.append({
                    "path": str(anchor_file.relative_to(vault_path)),
                    "project": project_name,
                    "action": action_text,
                    "modified": modified,
                    "type": "next_action"
                })
    
    return actions


def _extract_next_actions(file_path: Path) -> List[str]:
    """
    Extract action items from anchor file.
    
    Looks for the 'next_action' field in YAML frontmatter:
        ---
        next_action: Action description here
        ---
    
    Returns list of action strings (single item if next_action is found).
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return []
    
    actions = []
    
    # Check if file starts with YAML frontmatter
    if not content.startswith('---'):
        return actions
    
    # Extract frontmatter content
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not frontmatter_match:
        return actions
    
    frontmatter = frontmatter_match.group(1)
    
    # Look for next_action field
    next_action_match = re.search(r'^next_action:\s*(.+?)\s*$', frontmatter, re.MULTILINE)
    if next_action_match:
        action_text = next_action_match.group(1).strip()
        if action_text:
            actions.append(action_text)
    
    return actions
