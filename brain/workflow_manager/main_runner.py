#!/usr/bin/env python3
"""
Stage 4 - Processing & Scheduling Runner
Cron-driven execution for Second Brain system
"""

import os
import json
import shutil
import logging
import re
import sys
import yaml
from datetime import datetime
from pathlib import Path
from uuid import uuid4


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Add project root to Python path to allow module imports from other directories
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_MODE = False  # Set to True for test mode

# Vault paths

TEST_BASE = Path("_test_output")

INBOX_DIR = "00_inbox"
REVIEW_DIR = "01_review"
PROJECTS_DIR = "10_projects"
NOTES_DIR = "20_notes"
EVENTS_DIR = "30_events"
ARCHIVE_DIR = "99_archive"
SYSTEM_DIR = "_system"
STATE_FILE = "state.json"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise


def get_base_path():
    """Get base path depending on mode"""
    return VAULT_BASE / TEST_BASE if TEST_MODE else VAULT_BASE


def get_state_path():
    """Get state file path depending on mode"""
    base = get_base_path()
    return base / SYSTEM_DIR / STATE_FILE


def slugify(text):
    """Convert text to safe slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text[:50]


def get_timestamp():
    """Get current timestamp in YYYY-MM-DD_HHMMSS format"""
    return datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")


def get_iso_timestamp():
    """Get current timestamp in ISO8601 format"""
    return datetime.utcnow().isoformat() + "Z"


def ensure_dir(path):
    """Ensure directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)


def load_state():
    """Load system state from JSON file"""
    state_path = get_state_path()
    
    if not state_path.exists():
        default_state = {
            "processed_files": [],
            "last_run": None
        }
        ensure_dir(state_path.parent)
        save_state(default_state)
        return default_state
    
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load state: {e}")
        return {
            "processed_files": [],
            "last_run": None
        }


def save_state(state):
    """Save system state atomically"""
    state_path = get_state_path()
    ensure_dir(state_path.parent)
    
    temp_path = state_path.with_suffix('.tmp')
    
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        # Atomic replace
        shutil.move(str(temp_path), str(state_path))
    except Exception as e:
        print(f"[ERROR] Failed to save state: {e}")
        if temp_path.exists():
            temp_path.unlink()


def load_tags():
    """Load tags from tags.md file in vault root, create if not exists"""
    tags_path = VAULT_BASE / "tags.md"
    
    # Create default tags file if it doesn't exist
    if not tags_path.exists():
        default_tags_content = """# Tags"""
        ensure_dir(tags_path.parent)
        write_file(tags_path, default_tags_content)
        print(f"[TAGS] Created default tags file: {tags_path.name}")
    
    # Read and parse tags
    try:
        with open(tags_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse tags from markdown list format
        tags = []
        for line in content.split('\n'):
            line = line.strip()
            # Match lines starting with '- ' (markdown list items)
            if line.startswith('- '):
                tag = line[2:].strip()  # Remove '- ' prefix
                if tag and not tag.startswith('#'):  # Skip empty lines and section headers
                    tags.append(tag)
        
        print(f"[TAGS] Loaded {len(tags)} tags from {tags_path.name}")
        return tags
    except Exception as e:
        print(f"[ERROR] Failed to load tags: {e}")
        return []


def save_new_tags(new_tags, existing_tags):
    """Save new tags to tags.md file"""
    if not new_tags:
        return
    
    # Filter out tags that already exist
    tags_to_add = [tag for tag in new_tags if tag not in existing_tags]
    
    if not tags_to_add:
        print(f"[TAGS] No new tags to add")
        return
    
    tags_path = VAULT_BASE / "tags.md"
    
    try:
        # Read existing content
        with open(tags_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Append new tags
        lines = content.rstrip().split('\n')
        for tag in tags_to_add:
            lines.append(f"- {tag}")
        
        # Write back
        new_content = '\n'.join(lines) + '\n'
        write_file(tags_path, new_content)
        
        print(f"[TAGS] Added {len(tags_to_add)} new tag(s): {', '.join(tags_to_add)}")
    except Exception as e:
        print(f"[ERROR] Failed to save new tags: {e}")


def get_existing_projects():
    """Get list of existing project names from projects directory"""
    projects_path = VAULT_BASE / PROJECTS_DIR
    
    if not projects_path.exists():
        return []
    
    projects = []
    # Look for project anchor files (e.g., proj_123.md)
    for file_path in projects_path.glob("*.md"):
        # Extract project name from filename (without .md extension)
        project_name = file_path.stem
        projects.append(project_name)
    
    return projects


def get_inbox_files(state):
    """Get unprocessed inbox files sorted by name"""
    inbox_path = VAULT_BASE / INBOX_DIR
    print(f"[INBOX] Scanning for files in: {inbox_path}")
    if not inbox_path.exists():
        print(f"[INFO] Inbox directory not found: {inbox_path}")
        return []
    
    processed = set(state.get("processed_files", []))
    files = []
    
    for file_path in sorted(inbox_path.glob("*.md")):
        filename = file_path.name
        if filename not in processed:
            files.append(file_path)
        else:
            # Move processed file to archive
            archive_file(file_path)
    
    return files


def read_file_content(file_path):
    """Read file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read file {file_path}: {e}")
        return None


def write_file(path, content):
    """Write content to file"""
    try:
        ensure_dir(Path(path).parent)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write file {path}: {e}")
        return False


def archive_file(file_path):
    """Move file to archive (only in normal mode)"""
    if TEST_MODE:
        print(f"[TEST MODE] Would archive: {file_path.name}")
        return True
    
    try:
        archive_path = VAULT_BASE / ARCHIVE_DIR / file_path.name
        ensure_dir(archive_path.parent)
        shutil.move(str(file_path), str(archive_path))
        print(f"[ARCHIVE] Moved to archive: {file_path.name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to archive {file_path}: {e}")
        return False


def create_message_file(original_filename, title, summary, content, confidence, score, tags=None, extra_frontmatter=None):
    """Create formatted message file content"""
    frontmatter = {
        "source_file": original_filename,
        "confidence": confidence,
        "score": score,
        "created_at": get_iso_timestamp()
    }
    
    if extra_frontmatter:
        frontmatter.update(extra_frontmatter)
    
    lines = ["---"]
    for key, value in frontmatter.items():
        if value is not None:
            lines.append(f"{key}: {value}")
    
    # Add tags in frontmatter if present
    if tags and len(tags) > 0:
        tags_str = ", ".join([f"#{tag}" for tag in tags])
        lines.append(f"tags: {tags_str}")
    
    lines.append("---")
    # lines.append("")
    # lines.append(f"# {title}")
    lines.append("")
    lines.append(summary)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Original content:")
    lines.append("")
    lines.append(content)
    
    return "\n".join(lines)


def route_project(result, original_file, content, tags=None):
    """Route message to project"""
    base = get_base_path()
    project_name = result.get("project_name") or "default_project"
    project_slug = slugify(project_name)
    title = result.get("title", "Untitled")
    summary = result.get("summary", "")
    confidence = result.get("confidence", 0.0)
    score = result.get("score", 0.0)
    next_action = result.get("next_action")
    tags = tags or []
    
    timestamp = get_timestamp()
    title_slug = slugify(title)
    
    # Paths
    project_dir = base / PROJECTS_DIR / project_slug
    anchor_file = base / PROJECTS_DIR / f"{project_slug}.md"
    message_file = project_dir / f"{timestamp}_{title_slug}.md"
    
    # Create project directory
    ensure_dir(project_dir)
    
    # Create or update anchor file with next_action in frontmatter
    if not anchor_file.exists():
        anchor_frontmatter = ["---"]
        if next_action:
            anchor_frontmatter.append(f"next_action: {next_action}")
        anchor_frontmatter.append("---")
        anchor_frontmatter.append("")
        anchor_frontmatter.append(f"# {project_name}")
        anchor_frontmatter.append("")
        anchor_frontmatter.append("## Messages")
        anchor_frontmatter.append("")
        anchor_content = "\n".join(anchor_frontmatter)
        write_file(anchor_file, anchor_content)
        print(f"[PROJECT] Created anchor: {anchor_file.name}")
    elif next_action:
        # Update existing anchor file with next_action
        try:
            with open(anchor_file, 'r', encoding='utf-8') as f:
                anchor_content = f.read()
            
            # Check if frontmatter exists
            if anchor_content.startswith('---'):
                # Update existing frontmatter
                parts = anchor_content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter_lines = parts[1].strip().split('\n')
                    # Remove old next_action if exists
                    frontmatter_lines = [line for line in frontmatter_lines if not line.startswith('next_action:')]
                    # Add new next_action
                    frontmatter_lines.append(f"next_action: {next_action}")
                    parts[1] = '\n' + '\n'.join(frontmatter_lines) + '\n'
                    anchor_content = '---'.join(parts)
            else:
                # Add frontmatter at the beginning
                anchor_content = f"---\nnext_action: {next_action}\n---\n\n{anchor_content}"
            
            write_file(anchor_file, anchor_content)
            print(f"[PROJECT] Updated anchor with next_action: {anchor_file.name}")
        except Exception as e:
            print(f"[ERROR] Failed to update anchor file with next_action: {e}")
    
    # Append backlink to anchor
    try:
        with open(anchor_file, 'a', encoding='utf-8') as f:
            relative_link = f"{project_slug}/{message_file.name}"
            f.write(f"- [[{relative_link}|{title}]]\n")
    except Exception as e:
        print(f"[ERROR] Failed to update anchor file: {e}")
    
    # Create message file with next_action in frontmatter
    extra_frontmatter = {}
    if next_action:
        extra_frontmatter["next_action"] = next_action
    
    message_content = create_message_file(
        original_file.name,
        title,
        summary,
        content,
        confidence,
        score,
        tags,
        extra_frontmatter
    )
    
    if write_file(message_file, message_content):
        print(f"[PROJECT] Created message: {message_file}")
        return True
    
    return False


def route_note(result, original_file, content, tags=None):
    """Route message to notes"""
    base = get_base_path()
    title = result.get("title", "Untitled")
    summary = result.get("summary", "")
    confidence = result.get("confidence", 0.0)
    score = result.get("score", 0.0)
    tags = tags or []
    
    timestamp = get_timestamp()
    title_slug = slugify(title)
    
    note_file = base / NOTES_DIR / f"{timestamp}_{title_slug}.md"
    
    message_content = create_message_file(
        original_file.name,
        title,
        summary,
        content,
        confidence,
        score,
        tags
    )
    
    if write_file(note_file, message_content):
        print(f"[NOTE] Created: {note_file}")
        return True
    
    return False


def extract_clean_content(content):
    """Extract clean content after metadata section (after --- separator)"""
    try:
        # Split by --- to separate metadata from actual content
        if '---' in content:
            parts = content.split('---')
            # Get text after the --- separator and strip whitespace
            if len(parts) > 1:
                clean_text = '---'.join(parts[1:]).strip()
                return clean_text
        return content.strip()
    except Exception as e:
        print(f"[WARN] Failed to extract clean content: {e}")
        return content


def route_event(result, original_file, content, tags=None):
    """Route message to events"""
    base = get_base_path()
    title = result.get("title", "Untitled")
    summary = result.get("summary", "")
    confidence = result.get("confidence", 0.0)
    score = result.get("score", 0.0)
    event_datetime = result.get("datetime")
    due_date = result.get("due_date")
    time = result.get("time")
    all_day = result.get("all_day", True)
    tags = tags or []
    
    timestamp = get_timestamp()
    title_slug = slugify(title)
    
    event_file = base / EVENTS_DIR / f"{timestamp}_{title_slug}.md"
    
    # Clean content to remove metadata for events
    clean_content = extract_clean_content(content)
    
    extra_frontmatter = {
        "event_id": str(uuid4()),
        "gcal_id": None,
        "datetime": event_datetime,
        "due_date": due_date,
        "time": time,
        "all_day": all_day,
        "tags": tags
    }
    
    message_content = create_message_file(
        original_file.name,
        title,
        summary,
        clean_content,
        confidence,
        score,
        tags,
        extra_frontmatter
    )
    
    if write_file(event_file, message_content):
        print(f"[EVENT] Created: {event_file}")
        return True
    
    return False


def route_review(result, original_file, content):
    """Route message to review"""
    base = get_base_path()
    review_file = base / REVIEW_DIR / original_file.name
    
    if write_file(review_file, content):
        print(f"[REVIEW] Moved to review: {review_file}")
        return True
    
    return False


def get_recent_context(state, limit=5):
    """Get recent processed messages for context"""
    recent_context = []
    
    # Get last N processed files from state
    processed_files = state.get("processed_files", [])
    recent_files = processed_files[-limit:] if len(processed_files) > limit else processed_files
    
    # Load content from archive
    archive_path = VAULT_BASE / ARCHIVE_DIR
    
    for filename in recent_files:
        file_path = archive_path / filename
        if file_path.exists():
            content = read_file_content(file_path)
            if content:
                # Try to extract project name from routing log or state
                # For now, just include the text
                recent_context.append({
                    "text": content[:200],  # First 200 chars
                    "filename": filename
                })
    
    return recent_context


def process_file(file_path, state):
    """Process a single inbox file"""
    print(f"\n[PROCESSING] {file_path.name}")
    
    # Read content
    content = read_file_content(file_path)
    if content is None:
        return False
    
    # Run cognitive engine
    try:
        from cognitive_engine.cognitive_engine import process_input
        
        # Get existing projects from state or scan projects directory
        existing_projects = get_existing_projects()
        
        # Get recent context for better grouping
        recent_context = get_recent_context(state, limit=5)
        
        # Load available tags
        available_tags = load_tags()
        
        # Prepare input for cognitive engine
        input_data = {
            "id": file_path.stem,
            "text": content,
            "source": "inbox",
            "timestamp": get_iso_timestamp(),
            "existing_projects": existing_projects,
            "recent_context": recent_context,
            "available_tags": available_tags,
            "today": datetime.utcnow().strftime("%Y-%m-%d")
        }
        
        result = process_input(input_data)
        
        if not result:
            print(f"[ERROR] Cognitive engine returned no result")
            return False
        
        # Extract routing information
        routing = result.get("routing", {})
        msg_type = routing.get("type")
        confidence = result.get("confidence", 0.0)
        score = result.get("score", 0.0)
        summary = result.get("summary", "")
        tags = result.get("tags", [])
        
        print(f"[CLASSIFICATION] Type: {msg_type}, Confidence: {confidence:.2f}, Score: {score:.2f}")
        if tags:
            print(f"[TAGS] Generated tags: {', '.join(tags)}")
        
        # Save new tags to tags.md
        save_new_tags(tags, available_tags)
        
        # Prepare result dict for routing functions
        result_for_routing = {
            "type": msg_type,
            "title": result.get("summary", "Untitled")[:100],  # Use summary as title
            "summary": summary,
            "confidence": confidence,
            "score": score
        }
        
        # Add project info if applicable
        if msg_type == "project":
            project_info = routing.get("project", {})
            result_for_routing["project_name"] = project_info.get("name", "default_project")
            result_for_routing["next_action"] = project_info.get("next_action")
        
        # Add event info if applicable
        if msg_type == "event":
            event_info = routing.get("event", {})
            result_for_routing["due_date"] = event_info.get("due_date")
            result_for_routing["time"] = event_info.get("time")
            result_for_routing["all_day"] = event_info.get("all_day", True)
        
    except Exception as e:
        print(f"[ERROR] Cognitive engine failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Route based on type
    success = False
    
    if msg_type == "project":
        success = route_project(result_for_routing, file_path, content, tags)
    elif msg_type == "note":
        success = route_note(result_for_routing, file_path, content, tags)
    elif msg_type == "event":
        success = route_event(result_for_routing, file_path, content, tags)
    elif msg_type == "review":
        success = route_review(result_for_routing, file_path, content)
    else:
        print(f"[ERROR] Unknown message type: {msg_type}")
        return False
    
    if not success:
        return False
    
    # Archive file (only in normal mode)
    if not archive_file(file_path):
        return False
    
    # Update state
    if not TEST_MODE:
        if "processed_files" not in state:
            state["processed_files"] = []
        state["processed_files"].append(file_path.name)
        # Save state after each successful processing
        save_state(state)
    
    return True


def main():
    """Main runner function"""
    print("=" * 60)
    print("SECOND BRAIN - WORKFLOW RUNNER")
    print(f"Mode: {'TEST' if TEST_MODE else 'PRODUCTION'}")
    print(f"Time: {get_iso_timestamp()}")
    print("=" * 60)
    
    # Load state
    state = load_state()
    print(f"[STATE] Loaded. Processed files: {len(state.get('processed_files', []))}")
    print(f"[STATE] Last run: {state.get('last_run', 'Never')}")
    
    # Get inbox files
    files = get_inbox_files(state)
    print(f"\n[INBOX] Found {len(files)} unprocessed file(s)")
    
    if not files:
        print("[INFO] No files to process")
        return
    
    # Process each file
    processed_count = 0
    failed_count = 0
    
    for file_path in files:
        try:
            if process_file(file_path, state):
                processed_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"[ERROR] Unexpected error processing {file_path.name}: {e}")
            failed_count += 1
    
    # Update last run timestamp
    if not TEST_MODE and processed_count > 0:
        state["last_run"] = get_iso_timestamp()
        save_state(state)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"Processed: {processed_count}")
    print(f"Failed: {failed_count}")
    print(f"Total: {len(files)}")
    print("=" * 60)


if __name__ == "__main__":
    config_path = os.getenv("CONFIG_PATH", "../config.yaml")

    config = load_config(config_path)
    vault_path = config["paths"]["vault"]
    VAULT_BASE = Path(vault_path)

    main()
