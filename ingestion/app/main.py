"""
Main ingestion orchestrator for Slack pull-based ingestion.
Coordinates fetching, normalization, writing, and metadata tracking.
"""

import os
import sys
import yaml
import logging
from datetime import datetime
from pathlib import Path

from slack_connector import SlackConnector
from normalizer import Normalizer
from writer import Writer
from metadata import MetadataWriter
from media_downloader import MediaDownloader
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.debug(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise


def validate_config(config: dict) -> None:
    """Validate required configuration fields."""
    required_fields = ["poll", "slack", "paths"]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")
    
    if "lookback_minutes" not in config["poll"]:
        raise ValueError("Missing poll.lookback_minutes in config")
    
    if "channels" not in config["slack"] or not config["slack"]["channels"]:
        raise ValueError("Missing or empty slack.channels in config")
    
    if "inbox" not in config["paths"]:
        raise ValueError("Missing paths.inbox in config")
    
    if "metadata" not in config["paths"]:
        raise ValueError("Missing paths.metadata in config")
    
    if "attachments" not in config["paths"]:
        raise ValueError("Missing paths.attachments in config")


def main():
    """Main ingestion workflow."""
    logger.info("=== Slack Ingestion Started ===")
    run_started_at = datetime.utcnow()
    
    # Load configuration
    default_config = os.path.normpath(os.path.join(os.path.dirname(__file__), "../config.yaml"))
    config_path = os.getenv("CONFIG_PATH", default_config)
    config = load_config(config_path)
    validate_config(config)
    
    # Get secrets from environment
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        logger.error("SLACK_BOT_TOKEN environment variable is required")
        sys.exit(1)
    
    # Extract config values
    lookback_minutes = config["poll"]["lookback_minutes"]
    channels = config["slack"]["channels"]
    inbox_path = config["paths"]["inbox"]
    metadata_path = config["paths"]["metadata"]
    attachments_path = config["paths"]["attachments"]
    
    logger.info(f"Lookback window: {lookback_minutes} minutes")
    logger.debug(f"Channels to process: {len(channels)}")
    logger.debug(f"Attachments path: {attachments_path}")
    
    # Initialize components
    try:
        slack_connector = SlackConnector(slack_token)
        normalizer = Normalizer(slack_connector)
        media_downloader = MediaDownloader(attachments_path, slack_token)
        writer = Writer(inbox_path, media_downloader)
        metadata_writer = MetadataWriter(metadata_path)
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        sys.exit(1)
    
    # Process each channel
    total_fetched = 0
    total_written = 0
    total_skipped = 0
    
    for channel_id in channels:
        logger.info(f"Processing channel: {channel_id}")
        
        try:
            # Fetch messages
            messages = slack_connector.fetch_messages(channel_id, lookback_minutes)
            total_fetched += len(messages)
            
            # Normalize and write each message
            for message in messages:
                try:
                    normalized = normalizer.normalize(message, channel_id)
                    written = writer.write_message(normalized)
                    
                    if written:
                        total_written += 1
                    else:
                        total_skipped += 1
                
                except Exception as e:
                    logger.error(f"Failed to process message {message.get('ts')}: {e}")
                    # Continue processing other messages
        
        except Exception as e:
            logger.error(f"Failed to process channel {channel_id}: {e}")
            # Continue with other channels
    
    # Write run metadata
    run_finished_at = datetime.utcnow()
    
    try:
        metadata_writer.write_run_metadata(
            run_started_at=run_started_at,
            run_finished_at=run_finished_at,
            messages_fetched=total_fetched,
            messages_written=total_written,
            messages_skipped=total_skipped,
            channels=channels
        )
    except Exception as e:
        logger.error(f"Failed to write metadata: {e}")
    
    logger.info("=== Slack Ingestion Completed ===")
    logger.info(f"Total fetched: {total_fetched}")
    logger.info(f"Total written: {total_written}")
    logger.info(f"Total skipped: {total_skipped}")


if __name__ == "__main__":
    main()
