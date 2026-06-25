"""Unit tests for the report-generation logic in analysis.py."""

import io
import json

import pandas as pd
import pytest

from analysis import analyze_csv, analyze_dataframe


def sample_df():
    return pd.DataFrame(
        {
            "event_date": ["2024-01-01", "2024-01-02", "2024-01-02", "2024-02-15"],
            "event_type": ["webinar", "meetup", "webinar", "conference"],
            "attendees": [120, 45, 200, 530],
            "revenue": [1200.5, 0.0, 3000.0, 15000.75],
            "city": ["Nairobi", "Mombasa", "Nairobi", None],
        }
    )


def test_overview_counts():
    report = analyze_dataframe(sample_df(), filename="events.csv")
    o = report["overview"]
    assert o["rows"] == 4
    assert o["columns"] == 5
    assert o["numeric_columns"] == 2  # attendees, revenue
    assert o["datetime_columns"] == 1  # event_date auto-detected
    assert report["filename"] == "events.csv"


def test_missing_values_reported():
    report = analyze_dataframe(sample_df())
    city = next(c for c in report["columns"] if c["name"] == "city")
    assert city["missing"] == 1
    assert city["missing_pct"] == 25.0


def test_numeric_summary_values():
    report = analyze_dataframe(sample_df())
    attendees = next(n for n in report["numeric_summary"] if n["column"] == "attendees")
    assert attendees["min"] == 45
    assert attendees["max"] == 530
    assert attendees["sum"] == 895


def test_categorical_summary():
    report = analyze_dataframe(sample_df())
    event_type = next(
        c for c in report["categorical_summary"] if c["column"] == "event_type"
    )
    # webinar appears twice and should lead the counts.
    assert event_type["labels"][0] == "webinar"
    assert event_type["counts"][0] == 2


def test_time_series_built():
    report = analyze_dataframe(sample_df())
    assert report["time_series"] is not None
    assert report["time_series"]["column"] == "event_date"
    assert sum(report["time_series"]["counts"]) == 4


def test_report_is_json_serialisable():
    report = analyze_dataframe(sample_df())
    # Must not raise — the web layer relies on this.
    json.dumps(report)


def test_analyze_csv_from_filelike():
    csv = io.StringIO("a,b\n1,2\n3,4\n")
    report = analyze_csv(csv, filename="x.csv")
    assert report["overview"]["rows"] == 2


def test_empty_file_raises():
    with pytest.raises(ValueError):
        analyze_csv(io.StringIO(""))


def test_empty_dataframe_raises():
    with pytest.raises(ValueError):
        analyze_dataframe(pd.DataFrame())
