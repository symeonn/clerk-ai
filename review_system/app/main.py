"""Main entry point for review system."""

import os
import logging
import yaml
import sys
from pathlib import Path
from datetime import datetime

from scanner import scan_review_folder, scan_projects_for_next_actions
from selector import select_top_reminders
from writer import write_daily_note

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.debug(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise
    # return {
    #     "vault_path": str(vault_path),
    #     "max_reminders": int(os.getenv("MAX_REMINDERS", "3"))
    # }

def validate_config(config: dict) -> None:
    """Validate required configuration fields."""
    required_fields = ["vault_path", "max_reminders"]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")
    
    if "vault_path" not in config:
        raise ValueError("Missing vault_path in config")
    if "max_reminders" not in config:
        raise ValueError("Missing max_reminders in config")

def main():

    # Load configuration
    default_config = os.path.normpath(os.path.join(os.path.dirname(__file__), "../config.yaml"))
    config_path = os.getenv("CONFIG_PATH", default_config)
    config = load_config(config_path)
    validate_config(config)

    vault_path = config["vault_path"]
    max_reminders = config["max_reminders"]
    
    """Main execution flow."""
    print(f"[{datetime.now().isoformat()}] Starting review system...")
    
    print(f"Vault path: {vault_path}")
    
    # Step 1: Scan review folder
    print("Scanning 01_review/...")
    review_items = scan_review_folder(vault_path)
    print(f"Found {len(review_items)} review items")
    
    # Step 2: Scan projects for next actions
    print("Scanning 10_projects/ for next actions...")
    next_actions = scan_projects_for_next_actions(vault_path)
    print(f"Found {len(next_actions)} next actions")
    
    # Step 3: Select top reminders
    print(f"Selecting top {max_reminders} reminders...")
    reminders = select_top_reminders(review_items, next_actions, max_reminders)
    print(f"Selected {len(reminders)} reminders")
    
    # Step 4: Write daily note
    print("Writing daily note...")
    daily_note_path = write_daily_note(vault_path, reminders)
    print(f"Daily note created: {daily_note_path}")
    
    # Display selected reminders
    if reminders:
        print("\nSelected reminders:")
        for i, reminder in enumerate(reminders, 1):
            print(f"  {i}. {reminder['display']}")
    else:
        print("\nNo reminders selected")
    
    print(f"[{datetime.now().isoformat()}] Review system completed successfully")


if __name__ == "__main__":
    main()
