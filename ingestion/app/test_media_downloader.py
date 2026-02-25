"""
Test script for media downloader functionality.
Tests media extraction, download simulation, and markdown embedding.
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def test_media_extraction():
    """Test extracting media from a mock Slack message."""
    from media_downloader import MediaDownloader
    
    logger.info("=== Testing Media Extraction ===")
    
    # Mock Slack message with file attachments
    mock_message = {
        "ts": "1234567890.123456",
        "text": "Check out this image and audio!",
        "files": [
            {
                "id": "F0123456789",
                "name": "test_image.png",
                "title": "Test Image",
                "mimetype": "image/png",
                "url_private": "https://files.slack.com/files-pri/T123/F0123456789/test_image.png",
                "url_private_download": "https://files.slack.com/files-pri/T123/F0123456789/download/test_image.png",
                "size": 102400,
                "filetype": "png"
            },
            {
                "id": "F0123456790",
                "name": "test_audio.mp3",
                "title": "Test Audio",
                "mimetype": "audio/mpeg",
                "url_private": "https://files.slack.com/files-pri/T123/F0123456790/test_audio.mp3",
                "url_private_download": "https://files.slack.com/files-pri/T123/F0123456790/download/test_audio.mp3",
                "size": 512000,
                "filetype": "mp3"
            },
            {
                "id": "F0123456791",
                "name": "test_document.pdf",
                "title": "Test Document",
                "mimetype": "application/pdf",
                "url_private": "https://files.slack.com/files-pri/T123/F0123456791/test_document.pdf",
                "size": 204800,
                "filetype": "pdf"
            }
        ]
    }
    
    # Create temporary media downloader (without actual token)
    temp_path = Path("./test_attachments")
    temp_path.mkdir(exist_ok=True)
    
    try:
        downloader = MediaDownloader(str(temp_path), "test-token")
        
        # Extract media
        media_items = downloader.extract_media_from_message(mock_message)
        
        logger.info(f"Extracted {len(media_items)} media items")
        
        for item in media_items:
            logger.info(f"  - {item['name']} ({item['media_type']}, {item['mimetype']})")
        
        # Verify correct filtering (PDF should be excluded)
        assert len(media_items) == 2, f"Expected 2 media items, got {len(media_items)}"
        assert media_items[0]['media_type'] == 'image', "First item should be image"
        assert media_items[1]['media_type'] == 'audio', "Second item should be audio"
        
        logger.info("✓ Media extraction test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Media extraction test failed: {e}")
        return False
    finally:
        # Cleanup
        if temp_path.exists():
            import shutil
            shutil.rmtree(temp_path)


def test_markdown_building():
    """Test building markdown with media embeds."""
    from writer import Writer
    
    logger.info("=== Testing Markdown Building ===")
    
    # Mock downloaded media
    mock_media = [
        {
            "file_id": "F0123456789",
            "filename": "1234567890_123456_F0123456789_test_image.png",
            "relative_path": "Attachments/1234567890_123456_F0123456789_test_image.png",
            "media_type": "image",
            "title": "Test Image",
            "size": 102400
        },
        {
            "file_id": "F0123456790",
            "filename": "1234567890_123456_F0123456790_test_audio.mp3",
            "relative_path": "Attachments/1234567890_123456_F0123456790_test_audio.mp3",
            "media_type": "audio",
            "title": "Test Audio",
            "size": 512000
        }
    ]
    
    temp_path = Path("./test_inbox")
    
    # Mock frontmatter
    frontmatter = {
        "source": "slack",
        "source_id": "1234567890.123456",
        "author": "test_user",
        "timestamp": "2026-02-18T20:00:00Z",
        "channel": "C0123456789",
        "has_attachments": "true"
    }
    
    content = "Check out this image and audio!"
    
    try:
        temp_path.mkdir(exist_ok=True)
        
        writer = Writer(str(temp_path))
        
        # Build markdown
        markdown = writer._build_markdown(frontmatter, content, mock_media)
        
        logger.info("Generated markdown:")
        logger.info("-" * 60)
        logger.info(markdown)
        logger.info("-" * 60)
        
        # Verify markdown contains expected elements
        assert "---" in markdown, "Missing frontmatter delimiters"
        assert "source: slack" in markdown, "Missing source field"
        assert "has_attachments: true" in markdown, "Missing has_attachments field"
        assert "## Attachments" in markdown, "Missing attachments section"
        assert "![Test Image]" in markdown, "Missing image embed"
        assert "<audio controls" in markdown, "Missing audio embed"
        assert "Attachments/1234567890_123456_F0123456789_test_image.png" in markdown, "Missing image path"
        assert "Attachments/1234567890_123456_F0123456790_test_audio.mp3" in markdown, "Missing audio path"
        
        logger.info("✓ Markdown building test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Markdown building test failed: {e}")
        return False
    finally:
        # Cleanup
        if temp_path.exists():
            import shutil
            shutil.rmtree(temp_path)


def test_normalizer_with_media():
    """Test normalizer includes media information."""
    from normalizer import Normalizer
    from slack_connector import SlackConnector
    
    logger.info("=== Testing Normalizer with Media ===")
    
    # Mock message with files
    mock_message = {
        "ts": "1234567890.123456",
        "user": "U0123456789",
        "text": "Message with attachment",
        "files": [
            {
                "id": "F0123456789",
                "name": "test.png",
                "mimetype": "image/png"
            }
        ]
    }
    
    try:
        # Create mock connector (will fail on actual API calls, but that's ok for this test)
        connector = SlackConnector("test-token")
        normalizer = Normalizer(connector)
        
        # Normalize message
        normalized = normalizer.normalize(mock_message, "C0123456789")
        
        # Verify structure
        assert "raw_message" in normalized, "Missing raw_message field"
        assert "message_id" in normalized, "Missing message_id field"
        assert normalized["frontmatter"].get("has_attachments") == "true", "Missing has_attachments flag"
        assert normalized["raw_message"] == mock_message, "Raw message not preserved"
        
        logger.info("✓ Normalizer test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Normalizer test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("Starting media downloader tests...")
    logger.info("")
    
    results = []
    
    # Run tests
    results.append(("Media Extraction", test_media_extraction()))
    results.append(("Markdown Building", test_markdown_building()))
    results.append(("Normalizer with Media", test_normalizer_with_media()))
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info("")
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
