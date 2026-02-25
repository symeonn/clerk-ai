"""
Manages run-level metadata for ingestion tracking.
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Writes run-level metadata for each ingestion run."""
    
    def __init__(self, metadata_path: str):
        self.metadata_path = Path(metadata_path)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
    
    def write_run_metadata(
        self,
        run_started_at: datetime,
        run_finished_at: datetime,
        messages_fetched: int,
        messages_written: int,
        messages_skipped: int,
        channels: List[str]
    ) -> None:
        """
        Write metadata for a completed ingestion run.
        
        Args:
            run_started_at: When the run started
            run_finished_at: When the run finished
            messages_fetched: Total messages fetched from Slack
            messages_written: Messages written to inbox
            messages_skipped: Messages skipped (duplicates)
            channels: List of channel IDs processed
        """
        metadata = {
            "source": "slack",
            "run_started_at": run_started_at.isoformat() + "Z",
            "run_finished_at": run_finished_at.isoformat() + "Z",
            "messages_fetched": messages_fetched,
            "messages_written": messages_written,
            "messages_skipped": messages_skipped,
            "channels": channels
        }
        
        # Filename: run_<ISO8601>.json
        filename = f"run_{run_started_at.strftime('%Y%m%dT%H%M%S')}.json"
        filepath = self.metadata_path / filename
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            
            logger.debug(f"Metadata written: {filename}")
            # logger.info(f"Run summary: fetched={messages_fetched}, written={messages_written}, skipped={messages_skipped}")
        except Exception as e:
            logger.error(f"Failed to write metadata: {e}")
            raise
