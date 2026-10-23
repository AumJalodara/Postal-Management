"""
tests/test_clean_pincode_dataset.py
===================================
Unit tests for data cleaning logic in scripts/data/clean_pincode_dataset.py.
Verifies all project requirements:
  - Exact duplicate removal
  - NA normalization
  - PIN validation
  - Whitespace trimming
  - Safe coordinate parsing (DMS, °, N/E, embedded decimal spaces)
  - Rejection / nulling of unsafe coordinates (out-of-bounds >90, >180, malformed)
  - Preservation of valid records (including records with missing coordinates)
"""

import os
import sys
import tempfile
import csv
import pytest

# Ensure scripts directory is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.data.clean_pincode_dataset import (
    clean_text,
    validate_pincode,
    parse_coordinate,
    run_cleaning_pipeline,
    EXPECTED_COLUMNS,
)


class TestTextAndPINNormalization:
    """Test text stripping, missing sentinel normalization, and PIN code validation."""

    def test_whitespace_trimming(self):
        """Whitespace should be stripped without altering spelling or casing."""
        assert clean_text("  New Delhi S.O  ") == "New Delhi S.O"
        assert clean_text("Kothimir B.O ") == "Kothimir B.O"
        assert clean_text("   MAHARASHTRA   ") == "MAHARASHTRA"

    def test_na_normalization(self):
        """Literal missing sentinels (NA, N/A, NULL, empty) must be converted to None."""
        assert clean_text("NA") is None
        assert clean_text("na") is None
        assert clean_text("N/A") is None
        assert clean_text("NULL") is None
        assert clean_text("None") is None
        assert clean_text("") is None
        assert clean_text("   ") is None
        assert clean_text(None) is None

    def test_pincode_validation(self):
        """PIN codes must be exactly 6 numeric digits and preserved as strings."""
        # Valid cases (including leading zeroes)
        pin, is_valid = validate_pincode("110001")
        assert is_valid is True
        assert pin == "110001"
        assert isinstance(pin, str)

        pin, is_valid = validate_pincode(" 504273 ")
        assert is_valid is True
        assert pin == "504273"

        pin, is_valid = validate_pincode("012345")
        assert is_valid is True
        assert pin == "012345"

        # Invalid cases
        pin, is_valid = validate_pincode("11000")  # 5 digits
        assert is_valid is False

        pin, is_valid = validate_pincode("1100001")  # 7 digits
        assert is_valid is False

        pin, is_valid = validate_pincode("11000A")  # alphanumeric
        assert is_valid is False

        pin, is_valid = validate_pincode("110001.0")  # float notation
        assert is_valid is False

        pin, is_valid = validate_pincode("NA")
        assert is_valid is False
        assert pin is None


class TestCoordinateParsing:
    """Test coordinate parsing, safe normalization, and rejection of unsafe coordinates."""

    def test_safe_coordinate_parsing_direct_float(self):
        """Standard valid floats within geodetic range."""
        val, status, _ = parse_coordinate("19.3638689", "latitude")
        assert status == "valid_raw"
        assert abs(val - 19.3638689) < 1e-6

        val, status, _ = parse_coordinate("79.5376658", "longitude")
        assert status == "valid_raw"
        assert abs(val - 79.5376658) < 1e-6

    def test_safe_coordinate_parsing_trailing_degree(self):
        """Trailing degree symbol (e.g. Row 99244)."""
        val, status, _ = parse_coordinate("18.856818°", "latitude")
        assert status == "normalized_format"
        assert abs(val - 18.856818) < 1e-6

        val, status, _ = parse_coordinate("79.462604°", "longitude")
        assert status == "normalized_format"
        assert abs(val - 79.462604) < 1e-6

    def test_safe_coordinate_parsing_cardinal_suffixes(self):
        """Degree + Cardinal direction (Row 109142 and Row 161450)."""
        val, status, _ = parse_coordinate("28.430354° N", "latitude")
        assert status == "normalized_format"
        assert abs(val - 28.430354) < 1e-6

        val, status, _ = parse_coordinate("77.358526° E", "longitude")
        assert status == "normalized_format"
        assert abs(val - 77.358526) < 1e-6

        val, status, _ = parse_coordinate("25.43 N", "latitude")
        assert status == "normalized_format"
        assert abs(val - 25.43) < 1e-6

        val, status, _ = parse_coordinate("85.29 E", "longitude")
        assert status == "normalized_format"
        assert abs(val - 85.29) < 1e-6

    def test_safe_coordinate_parsing_internal_whitespace(self):
        """Internal whitespace between digits in decimal portion (Row 113103 and Row 144390)."""
        val, status, _ = parse_coordinate("28.4 32628", "latitude")
        assert status == "normalized_whitespace"
        assert abs(val - 28.432628) < 1e-6

        val, status, _ = parse_coordinate("94.28 28092", "longitude")
        assert status == "normalized_whitespace"
        assert abs(val - 94.2828092) < 1e-6

        val, status, _ = parse_coordinate("26.52 12743", "latitude")
        assert status == "normalized_whitespace"
        assert abs(val - 26.5212743) < 1e-6

        val, status, _ = parse_coordinate("95.30 54302", "longitude")
        assert status == "normalized_whitespace"
        assert abs(val - 95.3054302) < 1e-6

    def test_safe_coordinate_parsing_dms(self):
        """Degrees Minutes Seconds notation (Row 38790)."""
        val, status, _ = parse_coordinate("17°57'17.7", "latitude")
        assert status == "normalized_dms"
        expected = 17.0 + 57.0 / 60.0 + 17.7 / 3600.0
        assert abs(val - expected) < 1e-5

        val, status, _ = parse_coordinate("78°35'48.3", "longitude")
        assert status == "normalized_dms"
        expected = 78.0 + 35.0 / 60.0 + 48.3 / 3600.0
        assert abs(val - expected) < 1e-5

    def test_rejection_and_nulling_of_unsafe_coordinates(self):
        """Out of bounds (>90 lat, >180 lon) or malformed values must be rejected and set to null."""
        # Extreme unscaled decimal latitudes (e.g. Row 7095, Row 4809)
        val, status, _ = parse_coordinate("23724.290000000001", "latitude")
        assert status == "out_of_range"
        assert val is None

        val, status, _ = parse_coordinate("94.6318889", "latitude")
        assert status == "out_of_range"
        assert val is None

        val, status, _ = parse_coordinate("-95.5", "latitude")
        assert status == "out_of_range"
        assert val is None

        # Extreme unscaled longitudes
        val, status, _ = parse_coordinate("832015.52000000002", "longitude")
        assert status == "out_of_range"
        assert val is None

        val, status, _ = parse_coordinate("284.2000000", "longitude")
        assert status == "out_of_range"
        assert val is None

        val, status, _ = parse_coordinate("-185.0", "longitude")
        assert status == "out_of_range"
        assert val is None

        # Malformed non-numeric text
        val, status, _ = parse_coordinate("invalid_coord", "latitude")
        assert status == "malformed"
        assert val is None

    def test_missing_coordinates(self):
        """Missing coordinate sentinels return status 'missing' and None value."""
        val, status, _ = parse_coordinate("NA", "latitude")
        assert status == "missing"
        assert val is None

        val, status, _ = parse_coordinate("", "longitude")
        assert status == "missing"
        assert val is None


class TestPipelineIntegration:
    """End-to-end integration tests using synthetic sample data."""

    def test_pipeline_duplicate_removal_and_record_preservation(self):
        """
        Verify:
          - Exact full-row duplicates are removed.
          - Records sharing PIN or office name are NOT removed.
          - Records with missing or nulled coordinates are preserved.
          - Output CSV and quality report are properly created.
        """
        sample_rows = [
            EXPECTED_COLUMNS,
            # Row 1: Valid complete record
            ["Circle A", "Region A", "Div A", "Office 1", "110001", "PO", "Delivery", "Dist A", "State A", "28.6139", "77.2090"],
            # Row 2: Exact duplicate of Row 1 -> MUST BE REMOVED
            ["Circle A", "Region A", "Div A", "Office 1", "110001", "PO", "Delivery", "Dist A", "State A", "28.6139", "77.2090"],
            # Row 3: Same PIN and Office Name, but different division -> MUST BE PRESERVED
            ["Circle B", "Region B", "Div B", "Office 1", "110001", "BO", "Delivery", "Dist B", "State B", "28.7000", "77.3000"],
            # Row 4: NA placeholders in coordinates -> MUST BE PRESERVED with empty string coordinates
            ["Circle C", "NA", "Div C", "Office 2", "500001", "BO", "Delivery", "NA", "NA", "NA", "NA"],
            # Row 5: Formatting issues in coordinates -> MUST BE SAFELY NORMALIZED
            ["Circle D", "Region D", "Div D", "Office 3", "121004", "BO", "Delivery", "Dist D", "State D", "28.430354° N", "77.358526° E"],
            # Row 6: Out of bounds coordinate (>90) -> MUST BE PRESERVED with null coordinate
            ["Circle E", "Region E", "Div E", "Office 4", "785690", "BO", "Delivery", "Dist E", "State E", "94.6318889", "78.5000"],
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_csv = os.path.join(tmpdir, "raw.csv")
            processed_csv = os.path.join(tmpdir, "processed.csv")
            report_md = os.path.join(tmpdir, "report.md")

            with open(raw_csv, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(sample_rows)

            summary = run_cleaning_pipeline(raw_csv, processed_csv, report_md)

            # Assertions
            assert summary["raw_row_count"] == 6  # 6 input data rows
            assert summary["duplicate_rows_removed"] == 1  # Exactly Row 2
            assert summary["processed_row_count"] == 5  # 5 rows remaining

            # Read processed CSV
            with open(processed_csv, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                assert header == EXPECTED_COLUMNS
                data_rows = list(reader)

            assert len(data_rows) == 5

            # Verify Row 4 (NA normalization)
            r3 = data_rows[2]  # Office 2
            assert r3[3] == "Office 2"
            assert r3[1] == ""  # regionname was "NA"
            assert r3[7] == ""  # district was "NA"
            assert r3[8] == ""  # statename was "NA"
            assert r3[9] == ""  # latitude was "NA"
            assert r3[10] == ""  # longitude was "NA"

            # Verify Row 5 (Safely normalized coordinates)
            r4 = data_rows[3]  # Office 3
            assert r4[3] == "Office 3"
            assert abs(float(r4[9]) - 28.430354) < 1e-6
            assert abs(float(r4[10]) - 77.358526) < 1e-6

            # Verify Report generation
            assert os.path.exists(report_md)
            with open(report_md, "r", encoding="utf-8") as f:
                content = f.read()
            assert "## A. Input / Output Files" in content
            assert "## K. Explicit Audit & Compliance Statement" in content
