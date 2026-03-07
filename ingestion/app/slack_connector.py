"""
Slack API connector for fetching messages from channels.
Handles pagination and rate limiting.
"""

import os
import time
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)


class SlackConnector:
    """Fetches messages from Slack channels via Web API."""
    
    def __init__(self, token: str):
        if not token:
            raise ValueError("SLACK_BOT_TOKEN is required")
        
        self.token = token
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def fetch_messages(self, channel_id: str, lookback_minutes: int) -> List[Dict[str, Any]]:
        """
        Fetch messages from a channel within the lookback window.
        
        Args:
            channel_id: Slack channel ID (e.g., C0123456789)
            lookback_minutes: How far back to fetch messages
            
        Returns:
            List of message dictionaries (includes file attachments)
        """
        oldest_ts = (datetime.utcnow() - timedelta(minutes=lookback_minutes)).timestamp()
        
        logger.info(f"Fetching messages from channel {channel_id} since {oldest_ts}")
        
        messages = []
        cursor = None
        
        while True:
            params = {
                "channel": channel_id,
                "oldest": str(oldest_ts),
                "limit": 200  # Max per request
            }
            
            if cursor:
                params["cursor"] = cursor
            
            response = self._make_request("conversations.history", params)
            
            if not response.get("ok"):
                error = response.get("error", "unknown")
                logger.error(f"Slack API error for channel {channel_id}: {error}")
                raise RuntimeError(f"Slack API error: {error}")
            
            batch = response.get("messages", [])
            
            # Filter out bot messages unless they have a user field (user-authored)
            filtered = [
                msg for msg in batch
                if not msg.get("subtype") or msg.get("user")
            ]
            
            messages.extend(filtered)
            
            # Log media attachments found
            media_count = sum(1 for msg in filtered if msg.get("files"))
            if media_count > 0:
                logger.info(f"Fetched {len(filtered)} messages ({media_count} with media) from channel {channel_id}")
            else:
                logger.info(f"Fetched {len(filtered)} messages from channel {channel_id}")
            
            # Check for pagination
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        
        return messages
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user information by user ID.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            User info dictionary
        """
        response = self._make_request("users.info", {"user": user_id})
        
        if not response.get("ok"):
            logger.warning(f"Could not fetch user info for {user_id}")
            return {"id": user_id, "name": user_id}
        
        user = response.get("user", {})
        return {
            "id": user_id,
            "name": user.get("real_name") or user.get("name", user_id)
        }
    
    def reply_to_message(self, channel_id: str, thread_ts: str, text: str) -> bool:
        """
        Reply to a Slack message in a thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Timestamp of the message to reply to
            text: Reply text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self._make_request_post("chat.postMessage", {
                "channel": channel_id,
                "thread_ts": thread_ts,
                "text": text
            })
            
            if not response.get("ok"):
                error = response.get("error", "unknown")
                logger.error(f"Failed to reply to message {thread_ts}: {error}")
                return False
            
            logger.info(f"Replied to message {thread_ts} in channel {channel_id}")
            return True
        except Exception as e:
            logger.error(f"Exception while replying to message {thread_ts}: {e}")
            return False
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a GET request to Slack API with rate limit handling.
        
        Args:
            endpoint: API endpoint (e.g., 'conversations.history')
            params: Query parameters
            
        Returns:
            Response JSON
        """
        url = f"{self.base_url}/{endpoint}"
        
        # logger.info(f"Making request to {url} with params: {params}")

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            response = requests.get(url, headers=self.headers, params=params)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited. Sleeping for {retry_after} seconds")
                time.sleep(retry_after)
                retry_count += 1
                continue
            
            response.raise_for_status()
            return response.json()
        
        raise RuntimeError(f"Max retries exceeded for {endpoint}")
    
    def _make_request_post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a POST request to Slack API with rate limit handling.
        
        Args:
            endpoint: API endpoint (e.g., 'chat.postMessage')
            data: JSON data to send
            
        Returns:
            Response JSON
        """
        url = f"{self.base_url}/{endpoint}"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            response = requests.post(url, headers=self.headers, json=data)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited. Sleeping for {retry_after} seconds")
                time.sleep(retry_after)
                retry_count += 1
                continue
            
            response.raise_for_status()
            return response.json()
        
        raise RuntimeError(f"Max retries exceeded for {endpoint}")
