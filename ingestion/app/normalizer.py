"""
Normalizes Slack messages into canonical inbox format.
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Normalizer:
    """Converts Slack messages to standardized inbox format."""
    
    def __init__(self, slack_connector):
        self.slack_connector = slack_connector
        self._user_cache = {}
    
    def normalize(self, message: Dict[str, Any], channel_id: str) -> Dict[str, Any]:
        """
        Convert a Slack message to canonical inbox format.
        
        Args:
            message: Raw Slack message dictionary (may include file attachments)
            channel_id: Channel ID where message was posted
            
        Returns:
            Normalized message with metadata, content, and raw message for media processing
        """
        message_ts = message.get("ts", "")
        user_id = message.get("user", "unknown")
        text = message.get("text", "")
        
        # Get username (with caching)
        username = self._get_username(user_id)
        
        # Convert Slack timestamp to ISO8601
        try:
            timestamp_float = float(message_ts)
            timestamp_iso = datetime.utcfromtimestamp(timestamp_float).isoformat() + "Z"
            timestamp_filename = datetime.utcfromtimestamp(timestamp_float).strftime("%Y%m%dT%H%M%S")
        except (ValueError, TypeError):
            logger.warning(f"Invalid timestamp: {message_ts}")
            timestamp_iso = datetime.utcnow().isoformat() + "Z"
            timestamp_filename = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        
        # Generate filename
        # Format: YYYYMMDDTHHMMSS_slack_<message_id>.md
        # Use ts as message_id (replace . with _)
        message_id = message_ts.replace(".", "_")
        filename = f"{timestamp_filename}_slack_{message_id}.md"
        
        # Check for media attachments
        has_media = bool(message.get("files"))
        
        # Build frontmatter
        frontmatter = {
            "source": "slack",
            "source_id": message_ts,
            "author": username,
            "timestamp": timestamp_iso,
            "channel": channel_id
        }
        
        # Add media flag to frontmatter if present
        if has_media:
            frontmatter["has_attachments"] = "true"
        
        return {
            "filename": filename,
            "frontmatter": frontmatter,
            "content": text,
            "source_id": message_ts,
            "message_id": message_id,
            "raw_message": message  # Include raw message for media processing
        }
    
    def _get_username(self, user_id: str) -> str:
        """Get username with caching to reduce API calls."""
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        try:
            user_info = self.slack_connector.get_user_info(user_id)
            username = user_info.get("name", user_id)
            self._user_cache[user_id] = username
            return username
        except Exception as e:
            logger.warning(f"Failed to fetch username for {user_id}: {e}")
            return user_id
