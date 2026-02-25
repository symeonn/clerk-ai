# Media Attachments Implementation

## Overview

This document describes the implementation of automatic media attachment downloading and embedding for Slack messages in the ingestion layer.

## Features Implemented

### 1. Media Downloader Module (`media_downloader.py`)

A new module that handles:
- **Media Detection**: Identifies supported media types (images, audio, video) from Slack messages
- **File Downloads**: Downloads media files using authenticated Slack API requests
- **Deduplication**: Tracks downloaded files to avoid duplicate downloads
- **Error Handling**: Gracefully handles download failures without blocking message ingestion
- **Filename Generation**: Creates unique, safe filenames for downloaded media

**Supported Media Types:**
- **Images**: PNG, JPEG, GIF, WebP, BMP, SVG
- **Audio**: MP3, WAV, OGG, M4A, AAC, FLAC
- **Video**: MP4, WebM, OGG, QuickTime

### 2. Enhanced Slack Connector (`slack_connector.py`)

Updated to:
- Preserve file attachment information in fetched messages
- Log when messages contain media attachments
- Pass through complete message data including `files` array

### 3. Enhanced Normalizer (`normalizer.py`)

Updated to:
- Include `has_attachments` flag in frontmatter when media is present
- Preserve raw message data for media processing
- Add `message_id` field for organizing downloaded files

### 4. Enhanced Writer (`writer.py`)

Updated to:
- Accept optional `MediaDownloader` instance
- Download media files before writing markdown notes
- Embed media in markdown using appropriate syntax:
  - Images: `![title](path)` markdown syntax
  - Audio: HTML5 `<audio>` tags with fallback links
  - Video: HTML5 `<video>` tags with fallback links
- Continue writing notes even if media downloads fail

### 5. Configuration Updates

**config.yaml:**
- Added `paths.attachments` configuration for media storage location

**docker-compose.yml & docker-compose-inline-cron.yml:**
- Added volume mount for `Attachments` directory

### 6. Main Orchestrator (`main.py`)

Updated to:
- Initialize `MediaDownloader` with attachments path and Slack token
- Pass media downloader to `Writer` instance
- Validate attachments path in configuration

## File Structure

```
vault/
├── 00_inbox/                    # Message markdown files
│   ├── 20260218T120000_slack_1234567890_123456.md
│   └── _meta/                   # Run metadata
└── Attachments/                 # Downloaded media files
    ├── 1234567890_123456_F0123456789_image.png
    └── 1234567890_123456_F0123456790_audio.mp3
```

## Markdown Output Example

```markdown
---
source: slack
source_id: 1234567890.123456
author: john.doe
timestamp: 2026-02-18T12:00:00Z
channel: C0123456789
has_attachments: true
---

Check out this image and audio!

## Attachments

![Image Title](Attachments/1234567890_123456_F0123456789_image.png)

<audio controls src="Attachments/1234567890_123456_F0123456790_audio.mp3">
  Your browser does not support the audio element.
  [Download Audio Title](Attachments/1234567890_123456_F0123456790_audio.mp3)
</audio>
```

## Error Handling

The implementation includes robust error handling:

1. **Download Failures**: Logged but don't prevent message ingestion
2. **Duplicate Detection**: Checks existing files before downloading
3. **Network Errors**: Retries with exponential backoff (via requests library)
4. **Invalid URLs**: Logged and skipped
5. **Unsupported File Types**: Filtered out during extraction

## Slack Bot Permissions

The bot requires the following OAuth scopes:
- `channels:history` - Read public channel messages
- `users:read` - Resolve usernames
- `files:read` - **NEW**: Download media attachments

## Testing

A test suite (`test_media_downloader.py`) is provided to verify:
- Media extraction from Slack messages
- Markdown building with media embeds
- Normalizer integration with media flags

Run tests with:
```bash
cd ingestion/app
python test_media_downloader.py
```

## Deployment

1. **Update Slack Bot Permissions**: Add `files:read` scope in Slack App settings
2. **Create Attachments Directory**: `mkdir vault/Attachments`
3. **Rebuild Container**: `docker-compose build`
4. **Restart Service**: `docker-compose up -d`

## Performance Considerations

- **Caching**: Downloaded files are tracked to avoid re-downloading
- **Streaming**: Large files are downloaded in chunks to manage memory
- **Parallel Processing**: Each message is processed sequentially, but multiple channels can be processed in parallel
- **Storage**: Media files are stored with unique names to prevent conflicts

## Future Enhancements

Potential improvements:
- Add support for more file types (documents, archives)
- Implement thumbnail generation for images
- Add file size limits and validation
- Support for external media URLs (not just Slack-hosted)
- Compression for large media files
- Cleanup of orphaned media files

## Files Modified

1. `ingestion/app/media_downloader.py` - **NEW**
2. `ingestion/app/slack_connector.py` - Enhanced
3. `ingestion/app/normalizer.py` - Enhanced
4. `ingestion/app/writer.py` - Enhanced
5. `ingestion/app/main.py` - Enhanced
6. `ingestion/config.yaml` - Updated
7. `ingestion/docker-compose.yml` - Updated
8. `ingestion/docker-compose-inline-cron.yml` - Updated
9. `ingestion/README.md` - Updated
10. `ingestion/app/test_media_downloader.py` - **NEW**

## Summary

The media attachments feature is now fully integrated into the Slack ingestion pipeline. Messages with media attachments are automatically detected, downloaded, and embedded in the corresponding Obsidian markdown notes using relative paths. The implementation includes comprehensive error handling and deduplication to ensure reliable operation.
