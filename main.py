import os
import yaml
import json
import argparse
import sys
from pathlib import Path

def get_config():
    """Loads the configuration from config.yaml."""
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def get_base_path(config, test_mode):
    """Determines the base path for writes based on test mode."""
    if test_mode:
        path = Path(config['paths']['test_output'])
        # In test mode, mirror the vault structure
        for dir_name in ["00_inbox", "01_review", "10_projects", "20_notes", "30_events", "99_archive", "_system"]:
            (path / dir_name).mkdir(parents=True, exist_ok=True)
        return path
    return Path(config['paths']['vault'])

def initialize_system_file(file_path, schema_path):
    """Creates a system file with default content if it doesn't exist or is invalid."""
    if not file_path.exists() or os.path.getsize(file_path) == 0:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        default_content = {}
        if schema.get('type') == 'array':
            default_content = []
        
        with open(file_path, 'w') as f:
            json.dump(default_content, f, indent=4)
        print(f"Initialized {file_path}")


def main():
    """Main entry point for the Second Brain Core service."""
    parser = argparse.ArgumentParser(description="Second Brain Core Service")
    parser.add_argument("--test", action="store_true", help="Enable test mode, overriding config.yaml")
    args = parser.parse_args()

    config = get_config()
    
    # The --test flag from the command line takes precedence
    test_mode = args.test or config['flags']['test_mode']
    
    # This is a critical rule: redirect all writes to _test_output if in test mode
    base_path = get_base_path(config, test_mode)
    system_path = base_path / '_system'
    
    print(f"--- Second Brain Core ---")
    print(f"Test Mode: {test_mode}")
    print(f"Base Path: {base_path.resolve()}")
    print("-------------------------")

    # Rule: Ensure system files exist and conform to schemas (basic initialization)
    system_files = {
        "project_index.json": "vault/_system/schemas/project_index_schema.json",
        "routing_log.json": "vault/_system/schemas/routing_log_schema.json",
        "state.json": "vault/_system/schemas/system_state_schema.json"
    }

    for file, schema in system_files.items():
        initialize_system_file(system_path / file, Path(schema))
    
    print("System initialization complete.")
    # Future business logic would go here.
    # For now, the script just sets up the environment.

if __name__ == "__main__":
    main()
