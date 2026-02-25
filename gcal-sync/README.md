# Google Calendar ↔ Obsidian Vault Sync

Bidirectional synchronization between Google Calendar and Obsidian Vault events.

## Features

- **Two-way sync**: Changes in either Google Calendar or Obsidian are reflected in both
- **All-day events**: Supports both timed and all-day events
- **Conflict resolution**: Most recent change wins
- **Obsidian URLs**: Calendar events include direct links to notes
- **Configurable**: Separate calendar, custom sync intervals, timezone support

## Setup

### 1. Google Calendar API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Calendar API**
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials as `credentials.json`
6. Place `credentials.json` in the `gcal-sync/` directory

### 2. Get Calendar ID

1. Open [Google Calendar](https://calendar.google.com/)
2. Create or select a calendar for sync
3. Go to Calendar Settings → Integrate calendar
4. Copy the **Calendar ID** (e.g., `abc123@group.calendar.google.com`)

### 3. Configuration

```bash
cd gcal-sync
cp .env.example .env
```

Edit `.env`:
```env
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
VAULT_NAME=myvault
TZ=Europe/Warsaw
```

### 4. First Run (Authentication)

```bash
docker-compose run --rm gcal-sync python app/sync.py
```

This opens a browser for Google OAuth. After authentication, `token.json` is created.

### 5. Start Sync Service

```bash
docker-compose up -d
```

## Obsidian Note Format

### Timed Event
```markdown
---
title: Team Meeting
date: 2026-02-15
time: 14:00:00
gcal_event_id: abc123xyz
---

Discuss Q1 roadmap and priorities.
```

### All-Day Event
```markdown
---
title: Conference Day
date: 2026-03-20
all-day: true
gcal_event_id: def456uvw
---

Annual tech conference attendance.
```

## Sync Behavior

### Obsidian → Google Calendar
- New note with `date` → Creates calendar event
- Updated note → Updates calendar event
- Note content → Event description
- Obsidian URL added to event description

### Google Calendar → Obsidian
- New event → Creates note in `vault/30_events/`
- Updated event → Updates corresponding note
- Event description → Note content
- Calendar link added to note frontmatter

## Configuration

### Sync Interval
Edit `config.yaml`:
```yaml
sync:
  interval_minutes: 15  # Change to desired interval
```

### Events Folder
Edit `config.yaml`:
```yaml
obsidian:
  events_folder: "30_events"  # Change to desired folder
```

## Logs

```bash
docker-compose logs -f gcal-sync
```

## Troubleshooting

**Authentication fails**: Delete `token.json` and re-run first run step

**Events not syncing**: Check calendar ID in `.env` and verify API is enabled

**Permission errors**: Ensure vault volume is mounted with write permissions

## Architecture

- **Language**: Python 3.11
- **Sync Logic**: Timestamp-based conflict resolution
- **State Management**: JSON file tracks sync state
- **Deployment**: Docker container with volume mounts


autobuild on qnap
../QNAP/deploy-to-qnap.sh clerk-ai-gcal-sync