"""
Media downloader for Slack attachments (images, audio, etc.).
Handles downloading, deduplication, and storage of media files.
"""

import os
import logging
import hashlib
import requests
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Downloads and manages media attachments from Slack messages."""
    
    # Supported media types
    SUPPORTED_IMAGE_TYPES = {
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
        'image/webp', 'image/bmp', 'image/svg+xml'
    }
    
    SUPPORTED_AUDIO_TYPES = {
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 
        'audio/m4a', 'audio/aac', 'audio/flac', 'audio/mp4'
    }
    
    SUPPORTED_VIDEO_TYPES = {
        'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'
    }
    
    def __init__(self, attachments_path: str, slack_token: str):
        """
        Initialize media downloader.
        
        Args:
            attachments_path: Base path for storing attachments
            slack_token: Slack bot token for authenticated downloads
        """
        self.attachments_path = Path(attachments_path)
        self.attachments_path.mkdir(parents=True, exist_ok=True)
        
        self.slack_token = slack_token
        self.headers = {
            "Authorization": f"Bearer {slack_token}"
        }
        
        # Track downloaded files to avoid duplicates
        self._downloaded_files: Set[str] = self._load_existing_files()
        
        logger.info(f"MediaDownloader initialized with {len(self._downloaded_files)} existing files")
    
    def extract_media_from_message(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract media attachments from a Slack message.
        
        Args:
            message: Raw Slack message dictionary
            
        Returns:
            List of media attachment dictionaries with metadata
        """
        media_items = []
        
        # Check for files in the message
        files = message.get("files", [])
        
        for file_obj in files:
            mimetype = file_obj.get("mimetype", "")
            
            # Determine if this is a supported media type
            media_type = self._get_media_type(mimetype)
            if not media_type:
                logger.warning(f"Skipping unsupported file type: {mimetype} for message {message.get('ts')}")
                continue
            
            # Extract file information
            media_item = {
                "id": file_obj.get("id"),
                "name": file_obj.get("name"),
                "title": file_obj.get("title", ""),
                "mimetype": mimetype,
                "media_type": media_type,
                "url_private": file_obj.get("url_private"),
                "url_private_download": file_obj.get("url_private_download"),
                "size": file_obj.get("size", 0),
                "filetype": file_obj.get("filetype", "")
            }
            
            media_items.append(media_item)
        
        if media_items:
            logger.info(f"Found {len(media_items)} media attachment(s) in message")
        
        return media_items
    
    def download_media(self, media_item: Dict[str, Any], message_id: str) -> Optional[Dict[str, Any]]:
        """
        Download a media file and return its local path information.
        
        Args:
            media_item: Media item dictionary from extract_media_from_message
            message_id: Message ID for organizing files
            
        Returns:
            Dictionary with local file info or None if download failed
        """
        file_id = media_item.get("id")
        url = media_item.get("url_private_download") or media_item.get("url_private")
        
        if not url:
            logger.warning(f"No download URL for media item {file_id}")
            return None
        
        # Check if already downloaded
        if file_id in self._downloaded_files:
            logger.debug(f"Media file {file_id} already downloaded, skipping")
            # Return existing file info
            return self._get_existing_file_info(media_item, message_id)
        
        try:
            # Download the file
            logger.info(f"Downloading media: {media_item.get('name')} ({file_id})")
            print(f"Downloading from URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Generate safe filename
            filename = self._generate_filename(media_item, message_id)
            filepath = self.attachments_path / filename
            print(f"Saving media to: {filepath}")
            # Write file to disk
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Track downloaded file
            if file_id:
                self._downloaded_files.add(file_id)
            
            logger.info(f"Successfully downloaded: {filename}")
            
            return {
                "file_id": file_id,
                "filename": filename,
                "filepath": str(filepath),
                "relative_path": f"Attachments/{filename}",
                "media_type": media_item.get("media_type"),
                "title": media_item.get("title", ""),
                "size": media_item.get("size", 0)
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download media {file_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading media {file_id}: {e}")
            return None
    
    def download_all_media(self, message: Dict[str, Any], message_id: str) -> List[Dict[str, Any]]:
        """
        Extract and download all media from a message.
        
        Args:
            message: Raw Slack message dictionary
            message_id: Message ID for organizing files
            
        Returns:
            List of successfully downloaded media info dictionaries
        """
        media_items = self.extract_media_from_message(message)
        downloaded = []
        
        for media_item in media_items:
            result = self.download_media(media_item, message_id)
            if result:
                downloaded.append(result)
        
        return downloaded
    
    def _get_media_type(self, mimetype: str) -> Optional[str]:
        """Determine media type category from mimetype."""
        if mimetype in self.SUPPORTED_IMAGE_TYPES:
            return "image"
        elif mimetype in self.SUPPORTED_AUDIO_TYPES:
            return "audio"
        elif mimetype in self.SUPPORTED_VIDEO_TYPES:
            return "video"
        return None
    
    def _generate_filename(self, media_item: Dict[str, Any], message_id: str) -> str:
        """
        Generate a safe, unique filename for the media file.
        
        Format: {message_id}_{file_id}_{original_name}
        """
        file_id = media_item.get("id", "unknown")
        original_name = media_item.get("name", "file")
        
        # Sanitize filename
        safe_name = self._sanitize_filename(original_name)
        
        # Create unique filename
        filename = f"{message_id}_{file_id}_{safe_name}"
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Remove or replace unsafe characters in filename."""
        # Replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        name_part, ext = os.path.splitext(filename)
        if len(name_part) > 100:
            name_part = name_part[:100]
        
        return name_part + ext
    
    def _load_existing_files(self) -> Set[str]:
        """
        Load set of already downloaded file IDs.
        Extracts file IDs from existing filenames.
        """
        existing = set()
        
        if not self.attachments_path.exists():
            return existing
        
        for filepath in self.attachments_path.iterdir():
            if filepath.is_file():
                # Extract file_id from filename pattern: {message_id}_{file_id}_{name}
                parts = filepath.stem.split('_', 2)
                if len(parts) >= 2:
                    file_id = parts[1]
                    existing.add(file_id)
        
        return existing
    
    def _get_existing_file_info(self, media_item: Dict[str, Any], message_id: str) -> Dict[str, Any]:
        """Get file info for an already downloaded file."""
        filename = self._generate_filename(media_item, message_id)
        filepath = self.attachments_path / filename
        
        return {
            "file_id": media_item.get("id"),
            "filename": filename,
            "filepath": str(filepath),
            "relative_path": f"Attachments/{filename}",
            "media_type": media_item.get("media_type"),
            "title": media_item.get("title", ""),
            "size": media_item.get("size", 0)
        }
