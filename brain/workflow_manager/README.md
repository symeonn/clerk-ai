# Workflow Manager

Stage 4 – Processing & Scheduling for Second Brain system.

## Purpose

Cron-driven runner that processes inbox messages, classifies them via cognitive engine, routes outputs to vault folders, and maintains system state.

## Features

- Reads unprocessed files from `00_inbox/`
- Classifies via cognitive engine
- Routes to: projects, notes, events, or review
- Archives processed files
- Maintains idempotent state tracking
- Supports test mode for safe development

## Usage

### Production Mode

```bash
python workflow_manager/main_runner.py
```

### Test Mode

Edit [`main_runner.py`](main_runner.py:18):

```python
TEST_MODE = True
```

Then run:

```bash
python workflow_manager/main_runner.py
```

Test mode:
- Writes to `vault/_test_output/` instead of `vault/`
- Does NOT archive files
- Does NOT modify production state
- Keeps inbox files untouched

## Configuration

All paths configurable at top of [`main_runner.py`](main_runner.py:18-30):

```python
VAULT_BASE = Path("vault")
TEST_BASE = Path("_test_output")
INBOX_DIR = "00_inbox"
REVIEW_DIR = "01_review"
PROJECTS_DIR = "10_projects"
NOTES_DIR = "20_notes"
EVENTS_DIR = "30_events"
ARCHIVE_DIR = "99_archive"
SYSTEM_DIR = "_system"
```

## State Management

State file location:
- Production: `vault/_system/state.json`
- Test: `vault/_test_output/_system/state.json`

State structure:

```json
{
  "processed_files": ["file1.md", "file2.md"],
  "last_run": "2026-02-11T20:00:00.000Z"
}
```

## Routing Logic

| Type | Destination | Structure |
|------|-------------|-----------|
| `project` | `10_projects/` | `project_slug.md` + `project_slug/timestamp_slug.md` |
| `note` | `20_notes/` | `timestamp_slug.md` |
| `event` | `30_events/` | `timestamp_slug.md` |
| `review` | `01_review/` | Original filename preserved |

## Idempotency

Dual protection:
1. Files moved to `99_archive/` after processing
2. Filenames tracked in `state.json`

Files are never reprocessed.

## Error Handling

- Non-fatal errors logged to console
- Failed files remain in inbox
- Processing continues with next file
- State only updated on success

## Dependencies

- Python 3.7+
- Standard library only
- Requires: `cognitive_engine.cognitive_engine.process_message`

## Cron Setup

Example crontab (runs every 5 minutes):

```cron
*/5 * * * * cd /path/to/clerk-ai-v2 && python workflow_manager/main_runner.py >> logs/runner.log 2>&1
```
