#!/usr/bin/env python3
"""
Google Calendar <-> Obsidian Vault Bidirectional Sync
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
import frontmatter
from dateutil import parser as date_parser
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoogleCalendarSync:
    """Handles bidirectional sync between Google Calendar and Obsidian Vault"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the sync service"""
        self.config = self._load_config(config_path)
        self.service = self._authenticate()
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
        self.vault_path = Path(self.config['obsidian']['vault_path'])
        self.vault_name = self.config['obsidian']['vault_name']
        self.events_folder = self.config['obsidian']['events_folder']
        self.sync_state_file = Path(self.config['sync_state']['file'])
        self.sync_state = self._load_sync_state()
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _authenticate(self) -> any:
        """Authenticate with Google Calendar API"""
        creds = None
        token_file = self.config['google_calendar']['token_file']
        credentials_file = self.config['google_calendar']['credentials_file']
        scopes = self.config['google_calendar']['scopes']
        
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, scopes)
                creds = flow.run_local_server(port=0)
            
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        return build('calendar', 'v3', credentials=creds)
    
    def _load_sync_state(self) -> dict:
        """Load sync state from file"""
        if self.sync_state_file.exists():
            with open(self.sync_state_file, 'r') as f:
                return json.load(f)
        return {'events': {}, 'notes': {}}
    
    def _save_sync_state(self):
        """Save sync state to file"""
        with open(self.sync_state_file, 'w') as f:
            json.dump(self.sync_state, f, indent=2)
    
    def _get_obsidian_url(self, note_path: str) -> str:
        """Generate Obsidian URL for a note"""
        relative_path = note_path.replace('\\', '/')
        return f"obsidian://open?vault={self.vault_name}&file={relative_path}"
    
    def _parse_note_datetime(self, post) -> Tuple[Optional[datetime], bool]:
        """Parse datetime from note frontmatter, return (datetime, is_all_day)"""
        metadata = post.metadata
        
        # Check for all-day flag
        is_all_day = metadata.get('all-day', False)
        
        # Get date
        date_str = metadata.get('date')

        if not date_str:
            # Try due_date as fallback
            date_str = metadata.get('due_date')

        if not date_str:
            return None, False
        
        # Parse date
        try:
            dt = date_parser.parse(str(date_str))
            
            # Check for time field
            time_str = metadata.get('time')
            if time_str and not is_all_day:
                # Parse time and combine with date
                time_obj = date_parser.parse(str(time_str))
                dt = dt.replace(hour=time_obj.hour, minute=time_obj.minute, second=0)
                return dt, False
            else:
                # All-day event
                return dt.replace(hour=0, minute=0, second=0), True
        except Exception as e:
            logger.error(f"Error parsing date/time: {e}")
            return None, False
    
    def _create_calendar_event(self, note_path: Path, post) -> Optional[str]:
        """Create a Google Calendar event from an Obsidian note"""
        dt, is_all_day = self._parse_note_datetime(post)
        print(f"Creating gCal event for note: {note_path.name} (datetime: {dt}, all-day: {is_all_day})")
        if not dt:
            return None
        
        # Prepare event data
        title = post.metadata.get('title', note_path.stem)
        obsidian_url = self._get_obsidian_url(str(note_path.relative_to(self.vault_path)))
        
        event = {
            'summary': title,
            'description': post.content,
            'location': obsidian_url,
        }
        
        if is_all_day:
            # All-day event
            event['start'] = {'date': dt.strftime('%Y-%m-%d')}
            event['end'] = {'date': (dt + timedelta(days=1)).strftime('%Y-%m-%d')}
        else:
            # Timed event
            event['start'] = {
                'dateTime': dt.isoformat(),
                'timeZone': os.getenv('TZ', 'UTC'),
            }
            event['end'] = {
                'dateTime': (dt + timedelta(hours=1)).isoformat(),
                'timeZone': os.getenv('TZ', 'UTC'),
            }
        
        try:
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            logger.info(f"Created gCal event: {title}")
            return created_event['id']
        except Exception as e:
            logger.error(f"Error creating gCal event: {e}")
            return None
    
    def _update_calendar_event(self, event_id: str, note_path: Path, post):
        """Update an existing Google Calendar event"""
        dt, is_all_day = self._parse_note_datetime(post)
        if not dt:
            return
        
        title = post.metadata.get('title', note_path.stem)
        obsidian_url = self._get_obsidian_url(str(note_path.relative_to(self.vault_path)))
        
        event = {
            'summary': title,
            'description': post.content,
            'location': obsidian_url,
        }
        
        if is_all_day:
            event['start'] = {'date': dt.strftime('%Y-%m-%d')}
            event['end'] = {'date': (dt + timedelta(days=1)).strftime('%Y-%m-%d')}
        else:
            event['start'] = {
                'dateTime': dt.isoformat(),
                'timeZone': os.getenv('TZ', 'UTC'),
            }
            event['end'] = {
                'dateTime': (dt + timedelta(hours=1)).isoformat(),
                'timeZone': os.getenv('TZ', 'UTC'),
            }
        
        try:
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            logger.info(f"Updated calendar event: {title}")
        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
    
    def _create_obsidian_note(self, event: dict) -> Optional[Path]:
        """Create an Obsidian note from a Google Calendar event"""
        try:
            # Parse event datetime
            start = event['start']
            if 'dateTime' in start:
                dt = date_parser.parse(start['dateTime'])
                is_all_day = False
            else:
                dt = date_parser.parse(start['date'])
                is_all_day = True
            
            # Generate filename
            timestamp = dt.strftime('%Y-%m-%d_%H%M%S')
            title = event.get('summary', 'Untitled Event')
            safe_title = ''.join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in title)
            safe_title = safe_title[:50].strip().replace(' ', '_').lower()
            filename = f"{timestamp}_{safe_title}.md"
            
            # Create note path
            events_dir = self.vault_path / self.events_folder
            events_dir.mkdir(parents=True, exist_ok=True)
            note_path = events_dir / filename
            
            # Prepare frontmatter
            metadata = {
                'title': title,
                'date': dt.strftime('%Y-%m-%d'),
                'gcal_event_id': event['id'],
                'gcal_link': event.get('htmlLink', ''),
            }
            
            if is_all_day:
                metadata['all-day'] = True
            else:
                metadata['time'] = dt.strftime('%H:%M:%S')
            
            # Get description
            description = event.get('description', '')
            
            # Create note
            post = frontmatter.Post(description, **metadata)
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
            
            logger.info(f"Created Obsidian note: {filename}")
            return note_path
        except Exception as e:
            logger.error(f"Error creating Obsidian note: {e}")
            return None
    
    def _update_obsidian_note(self, note_path: Path, event: dict):
        """Update an existing Obsidian note from a Google Calendar event"""
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Parse event datetime
            start = event['start']
            if 'dateTime' in start:
                dt = date_parser.parse(start['dateTime'])
                is_all_day = False
            else:
                dt = date_parser.parse(start['date'])
                is_all_day = True
            
            # Update metadata
            post.metadata['title'] = event.get('summary', 'Untitled Event')
            post.metadata['date'] = dt.strftime('%Y-%m-%d')
            post.metadata['gcal_link'] = event.get('htmlLink', '')
            
            if is_all_day:
                post.metadata['all-day'] = True
                post.metadata.pop('time', None)
            else:
                post.metadata['time'] = dt.strftime('%H:%M:%S')
                post.metadata['all-day'] = False
            
            # Update content (preserve existing content if description hasn't changed)
            description = event.get('description', '')
            
            if description and description != post.content:
                post.content = description
            
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
            
            logger.info(f"Updated Obsidian note: {note_path.name}")
        except Exception as e:
            logger.error(f"Error updating Obsidian note: {e}")
    
    def sync_obsidian_to_calendar(self):
        """Sync Obsidian notes to Google Calendar"""
        events_dir = self.vault_path / self.events_folder
        print(f"Syncing Obsidian notes from: {events_dir}")

        if not events_dir.exists():
            logger.warning(f"Events folder not found: {events_dir}")
            return
        
        for note_path in events_dir.glob('*.md'):
            try:
                print(f"Reading note: {note_path.name}")
                with open(note_path, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                
                # Skip if no date or due_date
                if 'date' not in post.metadata and 'due_date' not in post.metadata:
                    print(f"Skipping note (no date): {note_path.name}")
                    continue
                
                note_key = str(note_path.relative_to(self.vault_path))
                note_mtime = note_path.stat().st_mtime
                print(f"Processing note: {note_path.name} (mtime: {note_mtime})")
                # Check if note has associated calendar event
                event_id = post.metadata.get('gcal_event_id')
                
                if event_id:
                    print(f"Note has associated event ID: {event_id}")
                    # Update existing event if note was modified
                    if note_key in self.sync_state['notes']:
                        last_sync = self.sync_state['notes'][note_key].get('mtime', 0)
                        if note_mtime > last_sync:
                            self._update_calendar_event(event_id, note_path, post)
                            self.sync_state['notes'][note_key] = {
                                'mtime': note_mtime,
                                'event_id': event_id
                            }
                    else:
                        # Track existing event
                        self.sync_state['notes'][note_key] = {
                            'mtime': note_mtime,
                            'event_id': event_id
                        }
                else:
                    # Create new calendar event
                    event_id = self._create_calendar_event(note_path, post)
                    if event_id:
                        # Update note with event ID
                        post.metadata['gcal_event_id'] = event_id
                        with open(note_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))
                        
                        self.sync_state['notes'][note_key] = {
                            'mtime': note_path.stat().st_mtime,
                            'event_id': event_id
                        }
            except Exception as e:
                logger.error(f"Error processing note {note_path}: {e}")
    
    def sync_calendar_to_obsidian(self):
        """Sync Google Calendar events to Obsidian notes"""
        try:
            # Get events from the last 30 days and next 90 days
            now = datetime.utcnow()
            time_min = (now - timedelta(days=30)).isoformat() + 'Z'
            time_max = (now + timedelta(days=90)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            for event in events:
                event_id = event['id']
                event_updated = date_parser.parse(event['updated']).timestamp()
                
                # Check if we have a note for this event
                note_path = None
                for note_key, note_data in self.sync_state['notes'].items():
                    if note_data.get('event_id') == event_id:
                        note_path = self.vault_path / note_key
                        break
                
                if note_path and note_path.exists():
                    # Update existing note if event was modified
                    if event_id in self.sync_state['events']:
                        last_sync = self.sync_state['events'][event_id].get('updated', 0)
                        if event_updated > last_sync:
                            self._update_obsidian_note(note_path, event)
                            self.sync_state['events'][event_id] = {
                                'updated': event_updated,
                                'note_path': str(note_path.relative_to(self.vault_path))
                            }
                    else:
                        # Track existing event
                        self.sync_state['events'][event_id] = {
                            'updated': event_updated,
                            'note_path': str(note_path.relative_to(self.vault_path))
                        }
                else:
                    # Create new note
                    note_path = self._create_obsidian_note(event)
                    if note_path:
                        note_key = str(note_path.relative_to(self.vault_path))
                        self.sync_state['events'][event_id] = {
                            'updated': event_updated,
                            'note_path': note_key
                        }
                        self.sync_state['notes'][note_key] = {
                            'mtime': note_path.stat().st_mtime,
                            'event_id': event_id
                        }
        except Exception as e:
            logger.error(f"Error syncing calendar to Obsidian: {e}")
    
    def run_sync(self):
        """Run a complete bidirectional sync"""
        logger.info("Starting sync...")
        
        # Sync Obsidian -> Google Calendar
        logger.info(">>>>> Syncing OBS -> gCal...")
        self.sync_obsidian_to_calendar()
        
        # Sync Google Calendar -> Obsidian
        logger.info(">>>>> Syncing gCal -> OBS...")
        self.sync_calendar_to_obsidian()
        
        # Save sync state
        self._save_sync_state()
        
        logger.info("Sync cycle completed.")
    
    def run_continuous(self):
        """Run continuous sync with configured interval"""
        interval = self.config['sync']['interval_minutes'] * 60
        
        logger.info(f"Starting continuous sync (interval: {self.config['sync']['interval_minutes']} minutes)")
        
        while True:
            try:
                self.run_sync()
            except Exception as e:
                logger.error(f"Error during sync: {e}")
            
            logger.info(f"Waiting {self.config['sync']['interval_minutes']} minutes until next sync...")
            time.sleep(interval)


def main():
    """Main entry point"""
    sync = GoogleCalendarSync()
    sync.run_continuous()


if __name__ == '__main__':
    main()
