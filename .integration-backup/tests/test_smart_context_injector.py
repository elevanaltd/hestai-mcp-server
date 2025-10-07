"""
Comprehensive tests for the Smart Context Injection System

Tests cover:
- Pattern detection with multi-stage matching
- Thread-safe caching operations
- ReDoS protection with timeout enforcement
- Circuit breaker functionality
- Configuration validation and hot-reload
- Performance guarantees (<50ms pattern matching, <100ms total)
- User notification generation
- Feature flag control
"""

# CONTEXT7_BYPASS: ARCH-003 - Test suite for architectural implementation
import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch

# Import the module under test
from utils.smart_context_injector import (
    CachedContent,
    CircuitBreaker,
    SmartContextInjector,
    get_smart_context_injector,
)


class TestPatternDetection:
    """Test pattern detection with multi-stage matching and confidence scoring."""

    def test_keyword_matching(self):
        """Test basic keyword pattern matching."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "test_pattern": {
                        "priority": 50,
                        "triggers": {"keywords": ["workflow", "phase", "execution"]},
                        "context_files": ["/test/file.md"],
                        "confidence_threshold": 0.25,  # Updated for new scoring system
                        "notification_template": "Test pattern matched",
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)
            matches = injector.detect_patterns("I need help with workflow execution", "chat")

            assert len(matches) == 1
            assert matches[0].pattern_name == "test_pattern"
            # Precise confidence: 0.4 weight * (2/3 keyword matches) = 0.26666...
            # CONTEXT7_BYPASS: T.R.A.C.E.D-IMPLEMENTATION - pytest approx for test precision
            import pytest

            assert matches[0].confidence == pytest.approx(0.26666666666666666, rel=1e-3)
            assert "workflow" in matches[0].matched_keywords
            assert "execution" in matches[0].matched_keywords

            os.unlink(f.name)

    def test_combination_matching(self):
        """Test keyword combination pattern matching."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "combo_pattern": {
                        "priority": 60,
                        "triggers": {"combinations": [["workflow", "phase"], ["agent", "capability"]]},
                        "context_files": ["/test/combo.md"],
                        "confidence_threshold": 0.15,  # Updated for new scoring system (0.4 * 1/2 = 0.2)
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Test matching combination
            matches = injector.detect_patterns("What is the workflow phase for B2?", "chat")
            assert len(matches) == 1
            assert ("workflow", "phase") in matches[0].matched_combinations

            # Test non-matching
            matches = injector.detect_patterns("Just workflow without other words", "chat")
            assert len(matches) == 0

            os.unlink(f.name)

    def test_regex_matching_with_timeout(self):
        """Test regex pattern matching with timeout protection."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "performance": {"pattern_match_timeout_ms": 10},
                "patterns": {
                    "regex_pattern": {
                        "priority": 70,
                        "triggers": {"regex_patterns": ["\\b(D[0-3]|B[0-5])\\b", "\\bworkflow\\s+phase\\b"]},
                        "context_files": ["/test/regex.md"],
                        "confidence_threshold": 0.05,  # Updated for new scoring system (0.2 * 1/2 = 0.1)
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)
            matches = injector.detect_patterns("Working on D1 and B2 phases", "chat")

            assert len(matches) == 1
            assert "\\b(D[0-3]|B[0-5])\\b" in matches[0].matched_regex

            os.unlink(f.name)

    def test_confidence_scoring(self):
        """Test confidence scoring with weighted factors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "multi_trigger": {
                        "priority": 80,
                        "triggers": {
                            "keywords": ["test", "pattern"],
                            "combinations": [["test", "pattern"]],
                            "regex_patterns": ["\\btest\\s+pattern\\b"],
                        },
                        "context_files": ["/test/multi.md"],
                        "confidence_threshold": 0.7,
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)
            matches = injector.detect_patterns("This is a test pattern example", "chat")

            assert len(matches) == 1
            # Should have high confidence since all triggers match
            assert matches[0].confidence > 0.9

            os.unlink(f.name)

    def test_priority_sorting(self):
        """Test that matches are sorted by priority then confidence."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "low_priority": {
                        "priority": 10,
                        "triggers": {"keywords": ["test"]},
                        "context_files": ["/test/low.md"],
                        "confidence_threshold": 0.1,
                    },
                    "high_priority": {
                        "priority": 90,
                        "triggers": {"keywords": ["test"]},
                        "context_files": ["/test/high.md"],
                        "confidence_threshold": 0.1,
                    },
                    "mid_priority": {
                        "priority": 50,
                        "triggers": {"keywords": ["test"]},
                        "context_files": ["/test/mid.md"],
                        "confidence_threshold": 0.1,
                    },
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)
            matches = injector.detect_patterns("test", "chat")

            assert len(matches) == 3
            assert matches[0].priority == 90
            assert matches[1].priority == 50
            assert matches[2].priority == 10

            os.unlink(f.name)


class TestThreadSafety:
    """Test thread-safe caching and concurrent operations."""

    def test_concurrent_cache_access(self):
        """Test that concurrent cache operations are thread-safe."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True, "caching_enabled": True},
                "patterns": {},
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Create test content
            test_content = CachedContent(
                content="Test content",
                token_count=10,
                loaded_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1),
                file_path="/test/file.md",
            )

            errors = []

            def cache_writer():
                """Write to cache repeatedly."""
                try:
                    for i in range(100):
                        with injector.cache_lock:
                            injector.content_cache[f"/test/file_{i}.md"] = test_content
                except Exception as e:
                    errors.append(e)

            def cache_reader():
                """Read from cache repeatedly."""
                try:
                    for i in range(100):
                        with injector.cache_lock:
                            _ = injector.content_cache.get(f"/test/file_{i}.md")
                except Exception as e:
                    errors.append(e)

            # Start multiple threads
            threads = []
            for _ in range(5):
                t1 = threading.Thread(target=cache_writer)
                t2 = threading.Thread(target=cache_reader)
                threads.extend([t1, t2])
                t1.start()
                t2.start()

            # Wait for all threads
            for t in threads:
                t.join()

            # No errors should occur
            assert len(errors) == 0

            os.unlink(f.name)

    def test_circuit_breaker_thread_safety(self):
        """Test that circuit breaker is thread-safe."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=1)

        errors = []

        def record_failures():
            """Record failures concurrently."""
            try:
                for _ in range(10):
                    breaker.record_failure("test_pattern")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def check_status():
            """Check circuit status concurrently."""
            try:
                for _ in range(10):
                    _ = breaker.is_open("test_pattern")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            t1 = threading.Thread(target=record_failures)
            t2 = threading.Thread(target=check_status)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0


class TestCircuitBreaker:
    """Test circuit breaker functionality for slow patterns."""

    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=1)

        # Initially closed
        assert not breaker.is_open("test_pattern")

        # Record failures
        breaker.record_failure("test_pattern")
        assert not breaker.is_open("test_pattern")  # Still closed

        breaker.record_failure("test_pattern")
        assert not breaker.is_open("test_pattern")  # Still closed

        breaker.record_failure("test_pattern")
        assert breaker.is_open("test_pattern")  # Now open

    def test_circuit_breaker_resets_after_timeout(self):
        """Test that circuit breaker resets after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, timeout_seconds=0.1)

        # Open the circuit
        breaker.record_failure("test_pattern")
        breaker.record_failure("test_pattern")
        assert breaker.is_open("test_pattern")

        # Wait for timeout
        time.sleep(0.15)

        # Should be closed again
        assert not breaker.is_open("test_pattern")

    def test_circuit_breaker_success_reduces_count(self):
        """Test that successes reduce failure count."""
        breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=1)

        # Record mixed results
        breaker.record_failure("test_pattern")  # count=1
        breaker.record_failure("test_pattern")  # count=2
        breaker.record_success("test_pattern")  # count=1 (reduced by success)
        breaker.record_failure("test_pattern")  # count=2

        # Should not be open yet (count=2, threshold=3)
        assert not breaker.is_open("test_pattern")

        # One more failure should trigger it
        breaker.record_failure("test_pattern")  # count=3, should open
        assert breaker.is_open("test_pattern")


class TestConfigurationHandling:
    """Test configuration validation, loading, and hot-reload."""

    def test_invalid_config_rejected(self):
        """Test that invalid configurations are rejected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Missing required 'version' field
            config = {"enabled": True, "patterns": {}}
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Should use default config due to validation failure
            assert not injector.config.get("enabled", False)

            os.unlink(f.name)

    def test_invalid_regex_rejected(self):
        """Test that configurations with invalid regex are rejected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "patterns": {"bad_regex": {"triggers": {"regex_patterns": ["[invalid(regex"]}}},  # Invalid regex
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Pattern should not be loaded due to invalid regex
            assert (
                "bad_regex" not in injector.patterns
                or len(injector.patterns["bad_regex"].get("_compiled_regex", [])) == 0
            )

            os.unlink(f.name)

    def test_hot_reload_configuration(self):
        """Test configuration hot-reload functionality."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Initial config
            config1 = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "pattern1": {
                        "triggers": {"keywords": ["test1"]},
                        "context_files": ["/test1.md"],
                        "confidence_threshold": 0.1,
                    }
                },
            }
            json.dump(config1, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Verify initial config
            assert "pattern1" in injector.patterns

            # Update config file
            config2 = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "pattern2": {
                        "triggers": {"keywords": ["test2"]},
                        "context_files": ["/test2.md"],
                        "confidence_threshold": 0.1,
                    }
                },
            }
            with open(f.name, "w") as f2:
                json.dump(config2, f2)

            # Hot reload
            injector.reload_config()

            # Verify new config
            assert "pattern2" in injector.patterns
            assert "pattern1" not in injector.patterns

            os.unlink(f.name)


class TestFeatureFlags:
    """Test feature flag control at global and per-tool levels."""

    def test_global_disable(self):
        """Test that global disable prevents all injection."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": False},  # Globally disabled
                "patterns": {
                    "test": {
                        "triggers": {"keywords": ["test"]},
                        "context_files": ["/test.md"],
                        "confidence_threshold": 0.1,
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Should not detect patterns when globally disabled
            matches = injector.detect_patterns("test", "chat")
            assert len(matches) == 0

            os.unlink(f.name)

    def test_per_tool_override(self):
        """Test per-tool feature flag overrides."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True, "per_tool_override": {"chat": True, "analyze": False}},
                "patterns": {
                    "test": {
                        "triggers": {"keywords": ["test"]},
                        "context_files": ["/test.md"],
                        "confidence_threshold": 0.1,
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Should work for chat
            matches = injector.detect_patterns("test", "chat")
            assert len(matches) == 1

            # Should not work for analyze
            matches = injector.detect_patterns("test", "analyze")
            assert len(matches) == 0

            os.unlink(f.name)

    def test_dry_run_mode(self):
        """Test dry run mode doesn't modify arguments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True, "dry_run_mode": True},
                "patterns": {
                    "test": {
                        "triggers": {"keywords": ["test"]},
                        "context_files": ["/test.md"],
                        "confidence_threshold": 0.1,
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            original_args = {"prompt": "test"}
            modified_args, notifications = injector.inject_context("test", "chat", original_args)

            # Arguments should be unchanged in dry run
            assert modified_args == original_args
            assert "[DRY RUN MODE]" in notifications[0]

            os.unlink(f.name)


class TestPerformance:
    """Test performance guarantees and timeouts."""

    def test_pattern_matching_timeout(self):
        """Test that pattern matching respects timeout."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "performance": {"pattern_match_timeout_ms": 1},  # Very short timeout
                "patterns": {
                    "slow_pattern": {
                        "triggers": {
                            # Complex regex that could be slow
                            "regex_patterns": ["(a+)+b" * 10]
                        },
                        "context_files": ["/test.md"],
                        "confidence_threshold": 0.1,
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Should complete even with complex regex due to timeout
            start = time.time()
            _ = injector.detect_patterns("a" * 100, "chat")
            elapsed = time.time() - start

            # Should be fast due to timeout
            assert elapsed < 0.1  # 100ms max

            os.unlink(f.name)

    @patch("utils.smart_context_injector.read_file_safely")
    def test_caching_performance(self, mock_read):
        """Test that caching improves performance."""
        mock_read.return_value = "Test content " * 1000  # Large content

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True, "caching_enabled": True},
                "patterns": {},
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # First load - should read from disk
            injector._cache_file("/test/file.md")
            assert mock_read.call_count == 1

            # Second load - should use cache
            injector._cache_file("/test/file.md")
            assert mock_read.call_count == 1  # No additional read

            os.unlink(f.name)


class TestIntegration:
    """Test full integration scenarios."""

    @patch("utils.smart_context_injector.read_file_safely")
    def test_full_injection_flow(self, mock_read):
        """Test complete injection flow from prompt to modified arguments."""
        mock_read.return_value = "This is the injected context content."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "workflow": {
                        "priority": 100,
                        "triggers": {"keywords": ["workflow", "phase"], "combinations": [["workflow", "phase"]]},
                        "context_files": ["/docs/workflow.md"],
                        "confidence_threshold": 0.5,
                        "notification_template": "Workflow docs included",
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            original_args = {"prompt": "How do I execute workflow phase D1?"}
            modified_args, notifications = injector.inject_context(original_args["prompt"], "chat", original_args)

            # Check modifications
            assert "Automatically Included Context" in modified_args["prompt"]
            assert "This is the injected context content" in modified_args["prompt"]
            assert "Workflow docs included" in notifications

            os.unlink(f.name)

    def test_metrics_tracking(self):
        """Test that metrics are properly tracked."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "version": "1.0.0",
                "enabled": True,
                "feature_flags": {"global_enabled": True},
                "patterns": {
                    "test": {
                        "triggers": {"keywords": ["test"]},
                        "context_files": ["/test.md"],
                        "confidence_threshold": 0.1,
                    }
                },
            }
            json.dump(config, f)
            f.flush()

            injector = SmartContextInjector(f.name)

            # Clear global metrics before test (fix for global state issue)
            # CONTEXT7_BYPASS: T.R.A.C.E.D-IMPLEMENTATION - Internal utils import for test fix
            from utils.smart_context_injector import metrics as global_metrics

            global_metrics["pattern_matches"].clear()

            # Perform some operations
            injector.detect_patterns("test", "chat")
            injector.detect_patterns("other", "chat")

            metrics = injector.get_metrics()

            # Check metrics
            assert metrics["pattern_matches"]["test"] == 1
            assert "cache_hit_ratio" in metrics
            assert "circuit_breaker_open" in metrics

            os.unlink(f.name)

    def test_singleton_pattern(self):
        """Test that get_smart_context_injector returns singleton."""
        injector1 = get_smart_context_injector()
        injector2 = get_smart_context_injector()

        assert injector1 is injector2
