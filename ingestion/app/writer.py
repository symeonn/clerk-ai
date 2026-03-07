"""
Writes normalized messages to inbox as immutable Markdown files.
Handles media attachment downloads and embedding.
"""

import os
import logging
from typing import Dict, Any, Set, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class Writer:
    """Writes messages to inbox with deduplication and media handling."""
    
    def __init__(self, inbox_path: str, media_downloader=None):
        self.inbox_path = Path(inbox_path)
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        
        # Optional media downloader for handling attachments
        self.media_downloader = media_downloader
        
        # Track existing source_ids for deduplication
        self._existing_ids = self._load_existing_ids()
    
    def write_message(self, normalized_msg: Dict[str, Any]) -> Optional[str]:
        """
        Write a normalized message to inbox with media attachments.
        
        Args:
            normalized_msg: Normalized message with filename, frontmatter, content, and raw_message
            
        Returns:
            Filename if written, None if skipped (duplicate)
        """
        source_id = normalized_msg["source_id"]
        
        # Check for duplicates
        if source_id in self._existing_ids:
            logger.debug(f"Skipping duplicate message: {source_id}")
            return None
        
        filename = normalized_msg["filename"]
        filepath = self.inbox_path / filename
        
        # Never overwrite existing files
        if filepath.exists():
            logger.warning(f"File already exists: {filename}, skipping")
            return None
        
        # Download media attachments if available
        downloaded_media = []
        if self.media_downloader and normalized_msg.get("raw_message"):
            try:
                message_id = normalized_msg.get("message_id", source_id.replace(".", "_"))
                downloaded_media = self.media_downloader.download_all_media(
                    normalized_msg["raw_message"],
                    message_id
                )
                if downloaded_media:
                    logger.info(f"Downloaded {len(downloaded_media)} media file(s) for message {source_id}")
            except Exception as e:
                logger.error(f"Failed to download media for message {source_id}: {e}")
                # Continue writing message even if media download fails
        
        # Build markdown content with media embeds
        content = self._build_markdown(
            normalized_msg["frontmatter"],
            normalized_msg["content"],
            downloaded_media
        )
        
        # Write atomically
        try:
            filepath.write_text(content, encoding="utf-8")
            self._existing_ids.add(source_id)
            logger.info(f"Written: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to write {filename}: {e}")
            raise
    
    def _build_markdown(self, frontmatter: Dict[str, Any], content: str,
                       media_files: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Build markdown file with YAML frontmatter and media embeds.
        
        Args:
            frontmatter: Message metadata
            content: Message text content
            media_files: List of downloaded media file info
            
        Returns:
            Complete markdown content
        """
        lines = ["---"]
        
        for key, value in frontmatter.items():
            lines.append(f"{key}: {value}")
        
        lines.append("---")
        lines.append("")
        
        # Add message content
        if content:
            lines.append(content)
        
        # Add media embeds if present
        if media_files:
            lines.append("")
            lines.append("## Attachments")
            lines.append("")
            
            for media in media_files:
                media_type = media.get("media_type", "file")
                relative_path = media.get("relative_path", "")
                title = media.get("title", media.get("filename", "attachment"))
                
                if media_type == "image":
                    # Embed image using markdown syntax
                    lines.append(f"![{title}]({relative_path})")
                elif media_type == "audio":
                    # Embed audio using HTML5 audio tag for better compatibility
                    lines.append(f'<audio controls src="{relative_path}">')
                    lines.append(f'  Your browser does not support the audio element.')
                    lines.append(f'  [Download {title}]({relative_path})')
                    lines.append(f'</audio>')
                elif media_type == "video":
                    # Embed video using HTML5 video tag
                    lines.append(f'<video controls src="{relative_path}" width="640">')
                    lines.append(f'  Your browser does not support the video element.')
                    lines.append(f'  [Download {title}]({relative_path})')
                    lines.append(f'</video>')
                else:
                    # Generic file link
                    lines.append(f"[{title}]({relative_path})")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def _load_existing_ids(self) -> Set[str]:
        """
        Load existing source_ids from inbox to prevent duplicates.
        Parses frontmatter of existing files.
        """
        existing_ids = set()
        
        if not self.inbox_path.exists():
            return existing_ids
        
        for filepath in self.inbox_path.glob("*.md"):
            try:
                content = filepath.read_text(encoding="utf-8")
                source_id = self._extract_source_id(content)
                if source_id:
                    existing_ids.add(source_id)
            except Exception as e:
                logger.warning(f"Could not parse {filepath.name}: {e}")
        
        logger.info(f"Loaded {len(existing_ids)} existing message IDs")
        return existing_ids
    
    def _extract_source_id(self, content: str) -> Optional[str]:
        """Extract source_id from frontmatter."""
        lines = content.split("\n")
        
        in_frontmatter = False
        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break
            
            if in_frontmatter and line.startswith("source_id:"):
                return line.split(":", 1)[1].strip()
        
        return None
