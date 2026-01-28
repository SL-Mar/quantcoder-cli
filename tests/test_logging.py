"""Tests for centralized logging and monitoring."""

import json
import logging
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from quantcoder.logging_config import (
    LoggingConfig,
    JSONFormatter,
    WebhookHandler,
    QuantCoderLogger,
    setup_logging,
    get_logger,
    get_log_files,
    log_with_context,
)
from quantcoder.config import Config, LoggingConfigSettings


class TestLoggingConfig:
    """Tests for LoggingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "standard"
        assert config.max_file_size_mb == 10
        assert config.backup_count == 5
        assert config.alert_on_error is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LoggingConfig(
            level="DEBUG",
            format="json",
            max_file_size_mb=20,
            backup_count=10,
            alert_on_error=True,
            webhook_url="https://example.com/webhook",
        )
        assert config.level == "DEBUG"
        assert config.format == "json"
        assert config.max_file_size_mb == 20
        assert config.webhook_url == "https://example.com/webhook"


class TestJSONFormatter:
    """Tests for JSON log formatter."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.module"
        assert data["message"] == "Test message"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_format_with_exception(self):
        """Test formatting a record with exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestWebhookHandler:
    """Tests for webhook alerting handler."""

    def test_handler_filters_by_level(self):
        """Test that handler only sends alerts for configured levels."""
        handler = WebhookHandler(
            webhook_url="https://example.com/webhook",
            alert_levels=["ERROR", "CRITICAL"]
        )

        # INFO should not trigger webhook
        info_record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Info message", args=(), exc_info=None
        )
        with patch('requests.post') as mock_post:
            handler.emit(info_record)
            mock_post.assert_not_called()

    @patch('requests.post')
    def test_handler_sends_error_alerts(self, mock_post):
        """Test that handler sends alerts for ERROR level."""
        mock_post.return_value = Mock(status_code=200)

        handler = WebhookHandler(
            webhook_url="https://example.com/webhook",
            alert_levels=["ERROR", "CRITICAL"]
        )

        error_record = logging.LogRecord(
            name="test.module", level=logging.ERROR, pathname="test.py",
            lineno=42, msg="Error occurred", args=(), exc_info=None
        )
        handler.emit(error_record)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args[1]['json']

        assert payload['level'] == 'ERROR'
        assert payload['message'] == 'Error occurred'
        assert payload['logger'] == 'test.module'

    @patch('requests.post')
    def test_handler_handles_webhook_failure(self, mock_post):
        """Test that webhook failures don't break logging."""
        mock_post.side_effect = Exception("Network error")

        handler = WebhookHandler(
            webhook_url="https://example.com/webhook",
            alert_levels=["ERROR"]
        )

        error_record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="Error", args=(), exc_info=None
        )

        # Should not raise exception
        handler.emit(error_record)


class TestQuantCoderLogger:
    """Tests for centralized logger manager."""

    def test_singleton_pattern(self):
        """Test that QuantCoderLogger uses singleton pattern."""
        logger1 = QuantCoderLogger()
        logger2 = QuantCoderLogger()
        assert logger1 is logger2

    def test_setup_creates_handlers(self, tmp_path):
        """Test that setup creates file handlers."""
        config = LoggingConfig(log_dir=tmp_path)

        # Reset singleton state for test
        QuantCoderLogger._initialized = False
        logger_manager = QuantCoderLogger()
        logger_manager.setup(verbose=False, config=config)

        # Check log files are created
        log_file = tmp_path / "quantcoder.log"
        json_log_file = tmp_path / "quantcoder.json.log"

        # Write a log message to create files
        test_logger = logging.getLogger("quantcoder.test")
        test_logger.info("Test message")

        assert log_file.exists() or json_log_file.exists()

        # Cleanup
        logger_manager.cleanup()


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_with_namespace(self):
        """Test that get_logger returns properly namespaced logger."""
        logger = get_logger("mymodule")
        assert logger.name == "quantcoder.mymodule"

    def test_already_namespaced_logger(self):
        """Test that already namespaced logger is not double-prefixed."""
        logger = get_logger("quantcoder.existing")
        assert logger.name == "quantcoder.existing"


class TestConfigLoggingSettings:
    """Tests for Config logging settings integration."""

    def test_config_has_logging_settings(self):
        """Test that Config includes logging settings."""
        config = Config()
        assert hasattr(config, 'logging')
        assert isinstance(config.logging, LoggingConfigSettings)

    def test_logging_settings_defaults(self):
        """Test default logging settings in Config."""
        config = Config()
        assert config.logging.level == "INFO"
        assert config.logging.format == "standard"
        assert config.logging.max_file_size_mb == 10
        assert config.logging.backup_count == 5

    def test_config_to_dict_includes_logging(self):
        """Test that to_dict includes logging config."""
        config = Config()
        data = config.to_dict()

        assert "logging" in data
        assert data["logging"]["level"] == "INFO"
        assert data["logging"]["format"] == "standard"

    def test_config_from_dict_with_logging(self):
        """Test that from_dict loads logging config."""
        data = {
            "logging": {
                "level": "DEBUG",
                "format": "json",
                "max_file_size_mb": 25,
                "backup_count": 15,
                "alert_on_error": True,
                "webhook_url": "https://test.com",
                "alert_levels": ["ERROR"],
            }
        }

        config = Config.from_dict(data)
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "json"
        assert config.logging.max_file_size_mb == 25
        assert config.logging.alert_on_error is True

    def test_get_logging_config_method(self, tmp_path):
        """Test get_logging_config returns LoggingConfig object."""
        # Mock dotenv module
        import sys
        mock_dotenv = MagicMock()
        original_dotenv = sys.modules.get('dotenv')
        sys.modules['dotenv'] = mock_dotenv

        try:
            config = Config()
            config.home_dir = tmp_path
            config.logging.level = "DEBUG"
            config.logging.format = "json"

            with patch.dict('os.environ', {}, clear=True):
                logging_config = config.get_logging_config()

            assert logging_config.level == "DEBUG"
            assert logging_config.format == "json"
            assert logging_config.log_dir == tmp_path / "logs"
        finally:
            # Restore original dotenv
            if original_dotenv:
                sys.modules['dotenv'] = original_dotenv
            else:
                sys.modules.pop('dotenv', None)


class TestAutoStatsPersistence:
    """Tests for AutoStats persistence."""

    def test_autostats_to_dict(self):
        """Test AutoStats serialization."""
        from quantcoder.autonomous.pipeline import AutoStats

        stats = AutoStats(
            total_attempts=10,
            successful=7,
            failed=3,
            avg_sharpe=1.5,
        )

        data = stats.to_dict()
        assert data['total_attempts'] == 10
        assert data['successful'] == 7
        assert data['failed'] == 3
        assert data['avg_sharpe'] == 1.5
        assert 'session_id' in data
        assert 'last_updated' in data

    def test_autostats_from_dict(self):
        """Test AutoStats deserialization."""
        from quantcoder.autonomous.pipeline import AutoStats

        data = {
            'total_attempts': 5,
            'successful': 4,
            'failed': 1,
            'avg_sharpe': 2.0,
            'session_id': 'test_session',
        }

        stats = AutoStats.from_dict(data)
        assert stats.total_attempts == 5
        assert stats.successful == 4
        assert stats.session_id == 'test_session'

    def test_autostats_save_load(self, tmp_path):
        """Test saving and loading AutoStats."""
        from quantcoder.autonomous.pipeline import AutoStats

        stats = AutoStats(
            total_attempts=10,
            successful=8,
            failed=2,
        )
        stats.save(tmp_path)

        # Check file exists
        assert (tmp_path / f"auto_stats_{stats.session_id}.json").exists()
        assert (tmp_path / "auto_stats_latest.json").exists()

        # Load and verify
        loaded = AutoStats.load_latest(tmp_path)
        assert loaded is not None
        assert loaded.total_attempts == 10
        assert loaded.successful == 8

    def test_autostats_list_sessions(self, tmp_path):
        """Test listing AutoStats sessions."""
        from quantcoder.autonomous.pipeline import AutoStats
        import time

        # Create multiple sessions
        for i in range(3):
            stats = AutoStats(total_attempts=i * 10)
            stats.session_id = f"session_{i}"
            stats.save(tmp_path)
            time.sleep(0.01)  # Small delay to ensure different mtimes

        sessions = AutoStats.list_sessions(tmp_path)
        assert len(sessions) == 3

    def test_autostats_success_rate(self):
        """Test success rate calculation."""
        from quantcoder.autonomous.pipeline import AutoStats

        stats = AutoStats(total_attempts=10, successful=7, failed=3)
        assert stats.success_rate == 0.7

        empty_stats = AutoStats()
        assert empty_stats.success_rate == 0.0
