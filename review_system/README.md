# Review System - Stage 5: Tap-on-the-Shoulder

Daily review mechanism that scans vault for actionable items and creates daily notes with top 3 reminders.

## Features

- Scans `01_review/` for unprocessed notes
- Extracts next actions from project anchor files in `10_projects/`
- Selects top 3 reminders based on priority and recency
- Creates/overwrites daily note (YYYY-MM-DD.md) in vault root
- Runs via cron (1-2x daily)
- Sends Slack notifications (future)

## Structure

```
review_system/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── scanner.py           # Vault scanning logic
│   ├── selector.py          # Reminder selection logic
│   └── writer.py            # Daily note writer
├── cron/
│   └── crontab              # Cron schedule
├── .env.example
├── config.yaml
├── Dockerfile
├── deploy-review-to-qnap.sh
└── requirements.txt
```

## Usage

```bash
python -m app.main
```

## Configuration

Set `VAULT_PATH` in `.env` or `config.yaml`.
