"""
Critical tests for bulk upload timestamp ordering.
Ensures files are processed in chronological order to maintain task context.
"""

from io import BytesIO

from app.routers.audio import _extract_timestamp_from_filename, _sort_files_by_timestamp


class TestTimestampExtraction:
    """Test timestamp extraction from filenames."""

    def test_extract_timestamp_pattern1(self):
        """Test YYYYMMDD_HHMMSS pattern."""
        filename = "recording_20240102_103045.wav"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 2
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45

    def test_extract_timestamp_pattern2(self):
        """Test YYYY-MM-DD_HH-MM-SS pattern."""
        filename = "voice_2024-01-02_10-30-45.m4a"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 2
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45

    def test_extract_timestamp_pattern3(self):
        """Test YYYYMMDDHHMMSS pattern (no separators)."""
        filename = "note_20240102103045.mp3"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 2

    def test_extract_timestamp_multiple_timestamps(self):
        """Test file with multiple timestamps uses first valid one."""
        filename = "backup_20240101_120000_recording_20240102_103045.wav"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        # Should extract the first timestamp
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_extract_timestamp_no_timestamp(self):
        """Test file without timestamp returns None."""
        filename = "my_recording.wav"
        result = _extract_timestamp_from_filename(filename)

        assert result is None

    def test_extract_timestamp_invalid_date(self):
        """Test invalid date returns None."""
        filename = "recording_20241399_259999.wav"  # Invalid month/day
        result = _extract_timestamp_from_filename(filename)

        assert result is None

    def test_extract_timestamp_with_prefix(self):
        """Test timestamp with various prefixes."""
        filenames = [
            "rec_20240102_103045.wav",
            "audio_20240102_103045.mp3",
            "voice_note_20240102_103045.m4a",
            "20240102_103045_meeting.wav",
        ]

        for filename in filenames:
            result = _extract_timestamp_from_filename(filename)
            assert result is not None, f"Failed to extract from {filename}"
            assert result.year == 2024

    def test_extract_timestamp_voice_recorder_format(self):
        """Test voice recorder format: R20250825234203.WAV"""
        filename = "R20250825234203.WAV"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 25
        assert result.hour == 23
        assert result.minute == 42
        assert result.second == 3

    def test_extract_timestamp_voice_recorder_lowercase(self):
        """Test voice recorder format with lowercase r."""
        filename = "r20250825234203.wav"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 25

    def test_extract_timestamp_voice_recorder_with_path(self):
        """Test voice recorder format with path prefix."""
        filename = "recordings/R20250825234203.WAV"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        assert result.year == 2025

    def test_extract_timestamp_voice_recorder_priority(self):
        """Test that R-prefix format takes priority over plain digits."""
        # If a file has both R-prefix and plain digits, R-prefix should win
        filename = "backup_20240101000000_R20250825234203.WAV"
        result = _extract_timestamp_from_filename(filename)

        assert result is not None
        # Should extract the R-prefix timestamp (2025)
        assert result.year == 2025
        assert result.month == 8
        assert result.day == 25


class TestFileSorting:
    """Test file sorting by timestamp."""

    def test_sort_files_chronological_order(self):
        """Test files are sorted earliest first."""
        from fastapi import UploadFile

        files = [
            UploadFile(filename="recording_20240103_100000.wav", file=BytesIO(b"3")),
            UploadFile(filename="recording_20240101_100000.wav", file=BytesIO(b"1")),
            UploadFile(filename="recording_20240102_100000.wav", file=BytesIO(b"2")),
        ]

        sorted_files = _sort_files_by_timestamp(files)

        assert len(sorted_files) == 3
        assert "20240101" in sorted_files[0].filename  # Earliest
        assert "20240102" in sorted_files[1].filename  # Middle
        assert "20240103" in sorted_files[2].filename  # Latest

    def test_sort_files_same_day_different_times(self):
        """Test sorting by time within same day."""
        from fastapi import UploadFile

        files = [
            UploadFile(filename="rec_20240101_150000.wav", file=BytesIO(b"3pm")),
            UploadFile(filename="rec_20240101_090000.wav", file=BytesIO(b"9am")),
            UploadFile(filename="rec_20240101_120000.wav", file=BytesIO(b"noon")),
        ]

        sorted_files = _sort_files_by_timestamp(files)

        assert "090000" in sorted_files[0].filename  # 9am first
        assert "120000" in sorted_files[1].filename  # Noon second
        assert "150000" in sorted_files[2].filename  # 3pm last

    def test_sort_files_with_no_timestamps(self):
        """Test files without timestamps maintain original order."""
        from fastapi import UploadFile

        files = [
            UploadFile(filename="file1.wav", file=BytesIO(b"1")),
            UploadFile(filename="file2.wav", file=BytesIO(b"2")),
            UploadFile(filename="file3.wav", file=BytesIO(b"3")),
        ]

        sorted_files = _sort_files_by_timestamp(files)

        # Should maintain original order
        assert sorted_files[0].filename == "file1.wav"
        assert sorted_files[1].filename == "file2.wav"
        assert sorted_files[2].filename == "file3.wav"

    def test_sort_files_mixed_timestamped_and_not(self):
        """Test timestamped files come first, then non-timestamped."""
        from fastapi import UploadFile

        files = [
            UploadFile(filename="file_no_timestamp.wav", file=BytesIO(b"x")),
            UploadFile(filename="rec_20240102_100000.wav", file=BytesIO(b"2")),
            UploadFile(filename="another_file.wav", file=BytesIO(b"y")),
            UploadFile(filename="rec_20240101_100000.wav", file=BytesIO(b"1")),
        ]

        sorted_files = _sort_files_by_timestamp(files)

        # Timestamped files first (in chronological order)
        assert "20240101" in sorted_files[0].filename
        assert "20240102" in sorted_files[1].filename
        # Then non-timestamped (original order preserved)
        assert sorted_files[2].filename == "file_no_timestamp.wav"
        assert sorted_files[3].filename == "another_file.wav"

    def test_sort_files_empty_list(self):
        """Test sorting empty list."""
        sorted_files = _sort_files_by_timestamp([])
        assert sorted_files == []

    def test_sort_files_single_file(self):
        """Test sorting single file."""
        from fastapi import UploadFile

        files = [UploadFile(filename="test.wav", file=BytesIO(b"data"))]
        sorted_files = _sort_files_by_timestamp(files)

        assert len(sorted_files) == 1
        assert sorted_files[0].filename == "test.wav"

    def test_sort_voice_recorder_format_files(self):
        """Test sorting voice recorder format files (R prefix)."""
        from fastapi import UploadFile

        files = [
            UploadFile(filename="R20250825150000.WAV", file=BytesIO(b"3pm")),
            UploadFile(filename="R20250825090000.WAV", file=BytesIO(b"9am")),
            UploadFile(filename="R20250825120000.WAV", file=BytesIO(b"noon")),
        ]

        sorted_files = _sort_files_by_timestamp(files)

        # Should be sorted by time: 9am, noon, 3pm
        assert "090000" in sorted_files[0].filename
        assert "120000" in sorted_files[1].filename
        assert "150000" in sorted_files[2].filename

    def test_sort_mixed_formats_with_voice_recorder(self):
        """Test sorting mix of voice recorder and other formats."""
        from fastapi import UploadFile

        files = [
            UploadFile(filename="R20250825120000.WAV", file=BytesIO(b"R-format")),
            UploadFile(filename="rec_20250825_100000.wav", file=BytesIO(b"standard")),
            UploadFile(filename="nodate.wav", file=BytesIO(b"no-ts")),
        ]

        sorted_files = _sort_files_by_timestamp(files)

        # Timestamped files first (10am then noon), then non-timestamped
        assert "100000" in sorted_files[0].filename
        assert "120000" in sorted_files[1].filename
        assert sorted_files[2].filename == "nodate.wav"


class TestBulkUploadOrdering:
    """Integration tests for bulk upload ordering."""

    def test_bulk_upload_processes_in_timestamp_order(self, client, test_db):
        """Test bulk upload processes files in chronological order."""
        # Create files with timestamps in reverse chronological order
        files = [
            ("files", ("rec_20240103_100000.wav", BytesIO(b"latest"), "audio/wav")),
            ("files", ("rec_20240101_100000.wav", BytesIO(b"earliest"), "audio/wav")),
            ("files", ("rec_20240102_100000.wav", BytesIO(b"middle"), "audio/wav")),
        ]

        response = client.post("/api/audio/bulk", files=files)

        assert response.status_code == 201
        data = response.json()

        # Check that files were processed
        assert data["total"] == 3
        assert data["successful"] >= 0  # May be 0 if ElevenLabs not configured

        # Verify they were processed in timestamp order
        # (by checking the order in results matches chronological order)
        filenames = [r["file_name"] for r in data["results"]]
        assert "20240101" in filenames[0]  # Earliest processed first
        assert "20240102" in filenames[1]  # Middle second
        assert "20240103" in filenames[2]  # Latest last

    def test_bulk_upload_maintains_context_order(self, client, test_db):
        """Test that task context is maintained across chronologically ordered files."""
        # Simulate: Morning meeting → Afternoon follow-up
        files = [
            (
                "files",
                ("meeting_20240101_143000.wav", BytesIO(b"afternoon"), "audio/wav"),
            ),  # Afternoon
            (
                "files",
                ("meeting_20240101_090000.wav", BytesIO(b"morning"), "audio/wav"),
            ),  # Morning
        ]

        response = client.post("/api/audio/bulk", files=files)

        assert response.status_code == 201
        data = response.json()

        # Morning recording should be processed first (for proper task context)
        filenames = [r["file_name"] for r in data["results"]]
        assert "090000" in filenames[0]
        assert "143000" in filenames[1]

    def test_bulk_upload_logs_ordering(self, client, test_db, caplog):
        """Test that bulk upload logs the file ordering."""
        import logging

        caplog.set_level(logging.INFO)

        files = [
            ("files", ("rec_20240102_100000.wav", BytesIO(b"2"), "audio/wav")),
            ("files", ("rec_20240101_100000.wav", BytesIO(b"1"), "audio/wav")),
        ]

        response = client.post("/api/audio/bulk", files=files)

        assert response.status_code == 201

        # Check that logging indicates timestamp ordering
        assert any(
            "timestamp order" in record.message.lower() for record in caplog.records
        )


class TestEdgeCases:
    """Test edge cases in timestamp ordering."""

    def test_files_with_same_timestamp(self):
        """Test files with identical timestamps maintain original order."""
        from fastapi import UploadFile

        files = [
            UploadFile(filename="rec_20240101_100000_part1.wav", file=BytesIO(b"1")),
            UploadFile(filename="rec_20240101_100000_part2.wav", file=BytesIO(b"2")),
            UploadFile(filename="rec_20240101_100000_part3.wav", file=BytesIO(b"3")),
        ]

        sorted_files = _sort_files_by_timestamp(files)

        # Should maintain original order for same timestamp
        assert "part1" in sorted_files[0].filename
        assert "part2" in sorted_files[1].filename
        assert "part3" in sorted_files[2].filename

    def test_different_timestamp_formats_mixed(self):
        """Test mixing different timestamp formats."""
        from fastapi import UploadFile

        files = [
            UploadFile(
                filename="file_20240103100000.wav", file=BytesIO(b"3")
            ),  # Pattern 3
            UploadFile(
                filename="rec_2024-01-01_10-00-00.wav", file=BytesIO(b"1")
            ),  # Pattern 2
            UploadFile(
                filename="voice_20240102_100000.wav", file=BytesIO(b"2")
            ),  # Pattern 1
        ]

        sorted_files = _sort_files_by_timestamp(files)

        # Should correctly sort regardless of format
        assert (
            "2024-01-01" in sorted_files[0].filename
            or "20240101" in sorted_files[0].filename
        )
        assert "20240102" in sorted_files[1].filename
        assert "20240103" in sorted_files[2].filename
