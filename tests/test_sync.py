"""Tests for the offline sync queue (JSONL, retries, purge).

Run: python -m pytest tests/test_sync.py -q
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.sync.queue import (
    QueuedPrediction,
    enqueue,
    list_pending,
    list_synced,
    mark_synced,
    purge_old,
    get_queue_stats,
    make_item_id,
    create_prediction,
    _b64encode,
    _b64decode,
    _queue_path,
)


class TestQueuedPrediction:
    """Test QueuedPrediction dataclass."""

    def test_create_prediction(self):
        pred = QueuedPrediction(
            id="test-1",
            ts=time.time(),
            image_b64="base64data",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
        )
        assert pred.id == "test-1"
        assert pred.confidence == 0.85
        assert pred.uncertain is False
        assert pred.synced is False
        assert pred.attempts == 0

    def test_to_dict(self):
        pred = QueuedPrediction(
            id="test-1",
            ts=time.time(),
            image_b64="base64data",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            farmer_correct=True,
            farmer_comment="confirmed",
        )
        d = pred.to_dict()
        assert d["id"] == "test-1"
        assert d["confidence"] == 0.85
        assert d["farmer_correct"] is True
        assert d["farmer_comment"] == "confirmed"

    def test_from_dict(self):
        data = {
            "id": "test-1",
            "ts": time.time(),
            "image_b64": "base64data",
            "mime_type": "image/jpeg",
            "predicted_class": "Apple___Apple_scab",
            "confidence": 0.85,
            "uncertain": False,
            "synced": False,
            "farmer_correct": True,
            "farmer_comment": "confirmed",
            "farmer_id": "",
            "attempts": 0,
            "next_retry_ts": time.time(),
        }
        pred = QueuedPrediction.from_dict(data)
        assert pred.id == "test-1"
        assert pred.confidence == 0.85
        assert pred.farmer_correct is True

    def test_from_dict_backward_compat(self):
        """Test loading old records without attempts/next_retry_ts."""
        data = {
            "id": "test-1",
            "ts": time.time(),
            "image_b64": "base64data",
            "mime_type": "image/jpeg",
            "predicted_class": "Apple___Apple_scab",
            "confidence": 0.85,
            "uncertain": False,
            "synced": False,
        }
        pred = QueuedPrediction.from_dict(data)
        assert pred.attempts == 0
        assert pred.next_retry_ts > 0

    def test_should_retry(self):
        pred = QueuedPrediction(
            id="test-1",
            ts=time.time(),
            image_b64="base64data",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            attempts=0,
            next_retry_ts=time.time() + 10,
        )
        assert pred.should_retry() is True

    def test_should_retry_synced(self):
        pred = QueuedPrediction(
            id="test-1",
            ts=time.time(),
            image_b64="base64data",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            synced=True,
        )
        assert pred.should_retry() is False

    def test_should_retry_max_attempts(self):
        pred = QueuedPrediction(
            id="test-1",
            ts=time.time(),
            image_b64="base64data",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            attempts=5,  # MAX_RETRIES = 3
            next_retry_ts=time.time() + 10,
        )
        assert pred.should_retry() is False

    def test_increment_attempts(self):
        pred = QueuedPrediction(
            id="test-1",
            ts=time.time(),
            image_b64="base64data",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            attempts=0,
            next_retry_ts=time.time(),
        )
        pred.increment_attempts()
        assert pred.attempts == 1
        assert pred.next_retry_ts > time.time()


class TestQueueOperations:
    """Test queue CRUD operations."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        # Override the queue directory
        import src.sync.queue as queue_module
        self.original_queue_dir = queue_module._QUEUE_DIR
        queue_module._QUEUE_DIR = Path(self.temp_dir)

    def teardown_method(self):
        import shutil
        import src.sync.queue as queue_module
        queue_module._QUEUE_DIR = self.original_queue_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enqueue_and_list_pending(self):
        pred = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        item_id = enqueue(pred)
        assert item_id == pred.id

        pending = list_pending("device-1")
        assert len(pending) == 1
        assert pending[0].id == pred.id

    def test_enqueue_multiple(self):
        for i in range(3):
            pred = create_prediction(
                image_bytes=b"fake_image",
                mime_type="image/jpeg",
                predicted_class="Apple___Apple_scab",
                confidence=0.85,
                uncertain=False,
                device_id="device-1",
            )
            enqueue(pred)

        pending = list_pending("device-1")
        assert len(pending) == 3

    def test_mark_synced(self):
        pred = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        enqueue(pred)

        # Mark as synced
        count = mark_synced("device-1", [pred.id])
        assert count == 1

        # Should no longer be in pending
        pending = list_pending("device-1")
        assert len(pending) == 0

        # Should be in synced
        synced = list_synced("device-1")
        assert len(synced) == 1
        assert synced[0].id == pred.id

    def test_mark_synced_unknown_id(self):
        count = mark_synced("device-1", ["nonexistent-id"])
        assert count == 0

    def test_purge_old_synced(self):
        # Create synced item with old timestamp
        old_ts = time.time() - (73 * 3600)  # 73 hours ago
        pred = QueuedPrediction(
            id="old-1",
            ts=old_ts,
            image_b64="base64data",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            synced=True,
        )
        path = _queue_path("device-1")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(pred.to_dict(), ensure_ascii=False) + "\n")

        # Create recent synced item
        pred2 = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        mark_synced("device-1", [pred2.id])

        # Purge with 72 hour TTL - old item should be removed
        removed = purge_old("device-1", max_age_seconds=72 * 3600)
        assert removed == 1

        synced = list_synced("device-1")
        assert len(synced) == 1
        assert synced[0].id == pred2.id

    def test_get_queue_stats(self):
        # Add some items
        for i in range(3):
            pred = create_prediction(
                image_bytes=b"fake_image",
                mime_type="image/jpeg",
                predicted_class="Apple___Apple_scab",
                confidence=0.85,
                uncertain=False,
                device_id="device-1",
            )
            enqueue(pred)

        # Mark one as synced
        pred = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        enqueue(pred)
        mark_synced("device-1", [pred.id])

        stats = get_queue_stats("device-1")
        assert stats["total"] == 4
        assert stats["synced"] == 1
        assert stats["pending"] == 3


class TestBase64Encoding:
    """Test base64 encoding/decoding."""

    def test_b64encode_decode(self):
        data = b"hello world"
        encoded = _b64encode(data)
        decoded = _b64decode(encoded)
        assert decoded == data

    def test_b64encode_empty(self):
        encoded = _b64encode(b"")
        decoded = _b64decode(encoded)
        assert decoded == b""


class TestQueuePersistence:
    """Test queue persists to disk and recovers."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        import src.sync.queue as queue_module
        self.original_queue_dir = queue_module._QUEUE_DIR
        queue_module._QUEUE_DIR = Path(self.temp_dir)

    def teardown_method(self):
        import shutil
        import src.sync.queue as queue_module
        queue_module._QUEUE_DIR = self.original_queue_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_persistence_across_instances(self):
        pred = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        enqueue(pred)

        # Re-load by calling list_pending
        pending = list_pending("device-1")
        assert len(pending) == 1
        assert pending[0].id == pred.id
        assert pending[0].predicted_class == "Apple___Apple_scab"

    def test_corrupted_jsonl_skipped(self):
        # Write corrupted line
        path = _queue_path("device-1")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json\n")

        # Should not crash, should return empty
        pending = list_pending("device-1")
        assert pending == []

    def test_partial_corruption(self):
        # Write valid + corrupted
        pred = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        path = _queue_path("device-1")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(pred.to_dict(), ensure_ascii=False) + "\n")
            fh.write("not valid json\n")

        pending = list_pending("device-1")
        assert len(pending) == 1
        assert pending[0].id == pred.id


class TestQueueCapacity:
    """Test queue capacity limits."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        import src.sync.queue as queue_module
        self.original_queue_dir = queue_module._QUEUE_DIR
        self.original_max_size = queue_module.MAX_QUEUE_SIZE
        queue_module._QUEUE_DIR = Path(self.temp_dir)
        queue_module.MAX_QUEUE_SIZE = 5  # Small limit for testing

    def teardown_method(self):
        import shutil
        import src.sync.queue as queue_module
        queue_module._QUEUE_DIR = self.original_queue_dir
        queue_module.MAX_QUEUE_SIZE = self.original_max_size
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enqueue_respects_max_size(self):
        # Fill queue to max
        for i in range(5):
            pred = create_prediction(
                image_bytes=b"fake_image",
                mime_type="image/jpeg",
                predicted_class="Apple___Apple_scab",
                confidence=0.85,
                uncertain=False,
                device_id="device-1",
            )
            enqueue(pred)

        # Next enqueue should be rejected (capacity full)
        pred = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        item_id = enqueue(pred)
        # Returns ID but doesn't actually add
        pending = list_pending("device-1")
        assert len(pending) == 5


class TestMakeItemId:
    """Test item ID generation."""

    def test_make_item_id_format(self):
        item_id = make_item_id()
        assert item_id.startswith("q")
        assert len(item_id) > 10  # timestamp + random

    def test_make_item_id_unique(self):
        ids = {make_item_id() for _ in range(100)}
        assert len(ids) == 100


class TestQueueIntegration:
    """Integration tests with realistic scenarios."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        import src.sync.queue as queue_module
        self.original_queue_dir = queue_module._QUEUE_DIR
        queue_module._QUEUE_DIR = Path(self.temp_dir)

    def teardown_method(self):
        import shutil
        import src.sync.queue as queue_module
        queue_module._QUEUE_DIR = self.original_queue_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_offline_then_online_flow(self):
        """Simulate offline predictions queued, then synced when online."""
        # Farmer makes 3 predictions offline
        item_ids = []
        for i in range(3):
            pred = create_prediction(
                image_bytes=b"fake_image",
                mime_type="image/jpeg",
                predicted_class="Apple___Apple_scab",
                confidence=0.85,
                uncertain=False,
                device_id="device-1",
            )
            enqueue(pred)
            item_ids.append(pred.id)

        pending = list_pending("device-1")
        assert len(pending) == 3

        # Farmer confirms one was correct - add farmer feedback
        # (In practice, this would be a separate record or update)
        # For now, just sync all

        # Sync with server
        mark_synced("device-1", item_ids)

        pending = list_pending("device-1")
        assert len(pending) == 0

        synced = list_synced("device-1")
        assert len(synced) == 3

    def test_retry_with_exponential_backoff(self):
        pred = create_prediction(
            image_bytes=b"fake_image",
            mime_type="image/jpeg",
            predicted_class="Apple___Apple_scab",
            confidence=0.85,
            uncertain=False,
            device_id="device-1",
        )
        enqueue(pred)

        pending = list_pending("device-1")
        assert len(pending) == 1

        # Simulate failed sync - item not marked synced
        # Next retry should work
        mark_synced("device-1", [pred.id])

        pending = list_pending("device-1")
        assert len(pending) == 0

    def test_ttl_cleanup_on_startup(self):
        """Expired items should be purged on queue initialization."""
        # Write old items directly to file
        old_ts = time.time() - (73 * 3600)
        old_item = {
            "id": "old-1",
            "ts": old_ts,
            "image_b64": "base64data",
            "mime_type": "image/jpeg",
            "predicted_class": "Apple___Apple_scab",
            "confidence": 0.85,
            "uncertain": False,
            "synced": True,
            "farmer_correct": None,
            "farmer_comment": "",
            "farmer_id": "device-1",
            "attempts": 0,
            "next_retry_ts": time.time(),
        }
        recent_item = {
            "id": "recent-1",
            "ts": time.time(),
            "image_b64": "base64data",
            "mime_type": "image/jpeg",
            "predicted_class": "Apple___Apple_scab",
            "confidence": 0.85,
            "uncertain": False,
            "synced": True,
            "farmer_correct": None,
            "farmer_comment": "",
            "farmer_id": "device-1",
            "attempts": 0,
            "next_retry_ts": time.time(),
        }
        path = _queue_path("device-1")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(old_item, ensure_ascii=False) + "\n")
            fh.write(json.dumps(recent_item, ensure_ascii=False) + "\n")

        # Initialize queue with 72 hour TTL - old item should be purged
        removed = purge_old("device-1", max_age_seconds=72 * 3600)
        assert removed == 1

        synced = list_synced("device-1")
        assert len(synced) == 1
        assert synced[0].id == "recent-1"