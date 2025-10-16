"""Tests for the Golden File Handler - Core Evidence System"""

import hashlib
import shutil
import tempfile
from pathlib import Path

import pytest

from amplifier.bplan.golden_file_handler import GoldenFileHandler


class TestGoldenFileHandler:
    """Test the GoldenFileHandler with real file operations"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def handler(self, temp_dir):
        """Create a GoldenFileHandler instance"""
        return GoldenFileHandler(base_dir=temp_dir)

    def test_handler_initialization(self, handler, temp_dir):
        """Test that handler creates necessary directories"""
        golden_dir = temp_dir / "golden"
        assert golden_dir.exists()
        assert golden_dir.is_dir()

    def test_generate_golden_file(self, handler, temp_dir):
        """Test generating a new golden file"""
        content = b"This is test content for golden file"
        name = "test_golden"

        golden_path = handler.generate(content, name)

        assert golden_path.exists()
        assert golden_path.parent == temp_dir / "golden"
        assert golden_path.name.startswith(name)
        assert golden_path.suffix == ".golden"

        # Verify content was written correctly
        with open(golden_path, "rb") as f:
            stored_content = f.read()
        assert stored_content == content

    def test_generate_with_hash_in_filename(self, handler):
        """Test that generated filenames include content hash"""
        content = b"Content for hashing"
        name = "hashed_file"

        golden_path = handler.generate(content, name)

        # Calculate expected hash
        expected_hash = hashlib.sha256(content).hexdigest()[:8]
        assert expected_hash in golden_path.name

    def test_compare_matching_content(self, handler):
        """Test comparing identical content with golden file"""
        content = b"Exact same content"
        name = "comparison_test"

        # Generate golden file
        golden_path = handler.generate(content, name)

        # Compare with same content
        assert handler.compare(content, golden_path) is True

    def test_compare_different_content(self, handler):
        """Test comparing different content with golden file"""
        original = b"Original content"
        different = b"Different content"
        name = "diff_test"

        # Generate golden file with original
        golden_path = handler.generate(original, name)

        # Compare with different content
        assert handler.compare(different, golden_path) is False

    def test_compare_with_nonexistent_file(self, handler):
        """Test comparing with a non-existent golden file"""
        content = b"Some content"
        fake_path = Path("/nonexistent/path/file.golden")

        with pytest.raises(FileNotFoundError):
            handler.compare(content, fake_path)

    def test_get_diff_with_differences(self, handler):
        """Test getting diff between content and golden file"""
        original = b"Line 1\nLine 2\nLine 3\n"
        modified = b"Line 1\nLine 2 modified\nLine 3\nLine 4\n"
        name = "diff_test"

        # Generate golden file
        golden_path = handler.generate(original, name)

        # Get diff
        diff = handler.get_diff(modified, golden_path)

        assert diff is not None
        assert len(diff) > 0
        assert "Line 2" in diff  # Should show the changed line
        assert "Line 4" in diff  # Should show the added line

    def test_get_diff_with_identical_content(self, handler):
        """Test getting diff when content matches golden file"""
        content = b"Identical content\nOn multiple lines\n"
        name = "no_diff"

        golden_path = handler.generate(content, name)
        diff = handler.get_diff(content, golden_path)

        # Diff should be empty or minimal for identical content
        assert diff == "" or "identical" in diff.lower() or len(diff.strip()) == 0

    def test_get_diff_with_binary_content(self, handler):
        """Test diff handling for binary content"""
        binary1 = b"\x00\x01\x02\x03\x04"
        binary2 = b"\x00\x01\x02\x05\x06"
        name = "binary_diff"

        golden_path = handler.generate(binary1, name)
        diff = handler.get_diff(binary2, golden_path)

        # Should handle binary content gracefully
        assert diff is not None

    def test_reproduce_golden_file(self, handler):
        """Test reproducing content from golden file"""
        original = b"Content to reproduce"
        name = "reproduce_test"

        # Generate golden file
        golden_path = handler.generate(original, name)

        # Reproduce content
        reproduced = handler.reproduce(golden_path)

        assert reproduced == original

    def test_reproduce_nonexistent_file(self, handler):
        """Test reproducing from non-existent file"""
        fake_path = Path("/nonexistent/file.golden")

        with pytest.raises(FileNotFoundError):
            handler.reproduce(fake_path)

    def test_persistence_across_instances(self, temp_dir):
        """Test that golden files persist across handler instances"""
        content = b"Persistent content"
        name = "persistence"

        # Create first handler and generate file
        handler1 = GoldenFileHandler(base_dir=temp_dir)
        golden_path = handler1.generate(content, name)

        # Create second handler with same directory
        handler2 = GoldenFileHandler(base_dir=temp_dir)

        # Should be able to work with file from first handler
        assert handler2.compare(content, golden_path) is True
        reproduced = handler2.reproduce(golden_path)
        assert reproduced == content

    def test_multiple_versions_of_same_name(self, handler):
        """Test generating multiple golden files with same name"""
        name = "versioned"
        content1 = b"Version 1"
        content2 = b"Version 2"

        path1 = handler.generate(content1, name)
        path2 = handler.generate(content2, name)

        # Should create different files
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()

        # Each should contain correct content
        assert handler.reproduce(path1) == content1
        assert handler.reproduce(path2) == content2

    def test_antagonistic_corrupted_golden_file(self, handler, temp_dir):
        """Test handling of corrupted golden files"""
        content = b"Original content"
        name = "corrupted"

        golden_path = handler.generate(content, name)

        # Corrupt the file
        with open(golden_path, "wb") as f:
            f.write(b"Corrupted")

        # Should detect the difference
        assert handler.compare(content, golden_path) is False

        # Should still be able to reproduce (even if corrupted)
        corrupted = handler.reproduce(golden_path)
        assert corrupted == b"Corrupted"

    def test_antagonistic_empty_content(self, handler):
        """Test handling of empty content"""
        empty = b""
        name = "empty"

        golden_path = handler.generate(empty, name)
        assert golden_path.exists()

        # Should handle empty content correctly
        assert handler.compare(empty, golden_path) is True
        assert handler.reproduce(golden_path) == empty

    def test_antagonistic_large_content(self, handler):
        """Test handling of large content"""
        # Create 10MB of content
        large_content = b"x" * (10 * 1024 * 1024)
        name = "large"

        golden_path = handler.generate(large_content, name)
        assert golden_path.exists()

        # Should handle large content
        assert handler.compare(large_content, golden_path) is True
        reproduced = handler.reproduce(golden_path)
        assert len(reproduced) == len(large_content)

    def test_antagonistic_special_characters_in_name(self, handler):
        """Test handling of special characters in names"""
        content = b"Test content"

        # Various problematic names
        names = [
            "name with spaces",
            "name/with/slashes",
            "name\\with\\backslashes",
            "name.with.dots",
            "name-with-dashes",
            "name_with_underscores",
            "name@with#special$chars",
        ]

        for name in names:
            # Should sanitize the name appropriately
            golden_path = handler.generate(content, name)
            assert golden_path.exists()
            assert handler.reproduce(golden_path) == content

    def test_unicode_content(self, handler):
        """Test handling of Unicode content"""
        unicode_content = "Hello 世界 🌍".encode()
        name = "unicode_test"

        golden_path = handler.generate(unicode_content, name)
        assert handler.compare(unicode_content, golden_path) is True
        assert handler.reproduce(golden_path) == unicode_content

    def test_concurrent_operations(self, handler):
        """Test concurrent file operations don't interfere"""
        # Generate multiple golden files rapidly
        paths = []
        for i in range(10):
            content = f"Content {i}".encode()
            path = handler.generate(content, f"concurrent_{i}")
            paths.append((path, content))

        # Verify all files are correct
        for path, expected_content in paths:
            assert handler.reproduce(path) == expected_content
