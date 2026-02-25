# Stage 3: Ingestion Layer (Pull-Based)

Pull-based Slack ingestion service that polls channels, normalizes messages, and writes immutable inbox files.

## Quick Start

1. **Set Slack token**:
   ```bash
   export SLACK_BOT_TOKEN=xoxb-your-token-here
   ```

2. **Configure channels** in `config.yaml`:
   ```yaml
   slack:
     channels:
       - C0123456789  # Your channel IDs
   ```

3. **Start service**:
   ```bash
   docker-compose up -d
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f
   ```

## Configuration

### Environment Variables
- `SLACK_BOT_TOKEN` (required): Slack Bot User OAuth Token

### config.yaml
- `poll.lookback_minutes`: Fetch window (default: 60)
- `slack.channels`: List of channel IDs to monitor
- `paths.inbox`: Inbox directory path
- `paths.metadata`: Metadata directory path
- `paths.attachments`: Media attachments directory path

### Cron Schedule
Edit `cron/crontab` to adjust polling frequency (default: every 15 minutes).

## Output Format

### Message Files
Location: `vault/00_inbox/YYYYMMDDTHHMMSS_slack_<message_id>.md`

```markdown
---
source: slack
source_id: 1234567890.123456
author: john.doe
timestamp: 2026-02-10T10:30:00Z
channel: C0123456789
has_attachments: true
---

Message content here

## Attachments

![Image Title](Attachments/1234567890_123456_F0123456789_image.png)

<audio controls src="Attachments/1234567890_123456_F0123456790_audio.mp3">
  Your browser does not support the audio element.
  [Download Audio Title](Attachments/1234567890_123456_F0123456790_audio.mp3)
</audio>
```

### Run Metadata
Location: `vault/00_inbox/_meta/run_<timestamp>.json`

```json
{
  "source": "slack",
  "run_started_at": "2026-02-10T10:30:00Z",
  "run_finished_at": "2026-02-10T10:30:15Z",
  "messages_fetched": 42,
  "messages_written": 30,
  "messages_skipped": 12,
  "channels": ["C0123456789"]
}
```

## Features

- **Deduplication**: Skips already-ingested messages via source_id tracking
- **Immutability**: Never overwrites existing files
- **Rate limiting**: Handles Slack API 429 responses with retry
- **Pagination**: Fetches all messages in lookback window
- **User resolution**: Caches usernames to reduce API calls
- **Media attachments**: Automatically downloads and embeds images, audio, and video files
- **Media deduplication**: Avoids re-downloading existing media files
- **Fail-loud**: Exits on misconfiguration or critical errors

### Media Attachment Support

The ingestion service automatically detects and downloads media attachments from Slack messages:

- **Supported formats**:
  - Images: PNG, JPEG, GIF, WebP, BMP, SVG
  - Audio: MP3, WAV, OGG, M4A, AAC, FLAC
  - Video: MP4, WebM, OGG, QuickTime

- **Storage**: Media files are stored in `vault/Attachments/` with unique filenames
- **Embedding**: Media is automatically embedded in markdown notes using relative paths
- **Error handling**: Failed downloads are logged but don't prevent message ingestion

## Slack Bot Setup

Required OAuth scopes:
- `channels:history` - Read public channel messages
- `users:read` - Resolve usernames
- `files:read` - Download media attachments

## Troubleshooting

**No messages appearing**: Check channel IDs in config.yaml and verify bot is member of channels.

**Rate limit errors**: Increase cron interval or reduce number of channels.

**Permission errors**: Verify SLACK_BOT_TOKEN has required scopes.

autobuild on qnap
../QNAP/deploy-to-qnap.sh clerk-ai-ingestion