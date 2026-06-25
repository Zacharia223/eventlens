"""Automated data-report generation for EventLens.

Given a CSV of event data, :func:`analyze_csv` returns a plain, JSON-serialisable
dictionary describing the dataset: an overview, per-column profiles, numeric and
categorical summaries, and ready-to-plot chart data. The web layer only has to
render this dict — it contains no pandas/numpy objects.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import pandas as pd

# Categorical columns with more distinct values than this are treated as
# high-cardinality (e.g. free text / IDs) and skipped for bar charts.
MAX_CATEGORY_CARDINALITY = 30
# How many of the most frequent values to show per categorical column.
TOP_N_CATEGORIES = 10
# Number of bins used when building numeric histograms.
HISTOGRAM_BINS = 12


def _clean_number(value: Any) -> Any:
    """Make a number safe for JSON (no NaN/inf) and tidy for display."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    # Keep integers as ints, round floats to something readable.
    if f == int(f):
        return int(f)
    return round(f, 4)


def _column_profiles(df: pd.DataFrame) -> list[dict[str, Any]]:
    total = len(df)
    profiles = []
    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())
        profiles.append(
            {
                "name": str(col),
                "dtype": _friendly_dtype(series),
                "missing": missing,
                "missing_pct": round((missing / total) * 100, 1) if total else 0.0,
                "unique": int(series.nunique(dropna=True)),
            }
        )
    return profiles


def _friendly_dtype(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"


def _numeric_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    summary = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if series.empty:
            continue
        summary.append(
            {
                "column": str(col),
                "count": int(series.count()),
                "min": _clean_number(series.min()),
                "max": _clean_number(series.max()),
                "mean": _clean_number(series.mean()),
                "median": _clean_number(series.median()),
                "std": _clean_number(series.std()),
                "sum": _clean_number(series.sum()),
            }
        )
    return summary


def _numeric_histograms(df: pd.DataFrame) -> list[dict[str, Any]]:
    charts = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        # A histogram needs spread; skip constant or near-empty columns.
        if series.empty or series.nunique() < 2:
            continue
        counts, edges = _histogram(series, HISTOGRAM_BINS)
        labels = [
            f"{_clean_number(edges[i])}–{_clean_number(edges[i + 1])}"
            for i in range(len(counts))
        ]
        charts.append({"column": str(col), "labels": labels, "counts": counts})
    return charts


def _histogram(series: pd.Series, bins: int) -> tuple[list[int], list[float]]:
    binned = pd.cut(series, bins=bins)
    counts = binned.value_counts(sort=False)
    edges: list[float] = [float(interval.left) for interval in counts.index]
    edges.append(float(counts.index[-1].right))
    return [int(c) for c in counts.tolist()], edges


def _categorical_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    summary = []
    candidate_cols = df.select_dtypes(exclude="number").columns
    for col in candidate_cols:
        series = df[col].dropna()
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        n_unique = series.nunique()
        if n_unique == 0 or n_unique > MAX_CATEGORY_CARDINALITY:
            continue
        counts = series.astype(str).value_counts().head(TOP_N_CATEGORIES)
        summary.append(
            {
                "column": str(col),
                "labels": [str(v) for v in counts.index.tolist()],
                "counts": [int(c) for c in counts.tolist()],
            }
        )
    return summary


def _detect_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort: parse object columns that look like dates into datetimes."""
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        sample = df[col].dropna().head(25)
        if sample.empty:
            continue
        with warnings.catch_warnings():
            # We deliberately let pandas infer mixed/unknown date formats here.
            warnings.simplefilter("ignore", UserWarning)
            parsed = pd.to_datetime(df[col], errors="coerce")
        # Treat the column as a date only if most non-null values parsed.
        non_null = df[col].notna().sum()
        if non_null and parsed.notna().sum() >= 0.8 * non_null:
            df[col] = parsed
    return df


def _time_series(df: pd.DataFrame) -> dict[str, Any] | None:
    """Build a count-per-period series from the first datetime column."""
    datetime_cols = [
        c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])
    ]
    if not datetime_cols:
        return None

    col = datetime_cols[0]
    dates = df[col].dropna()
    if dates.empty:
        return None

    span_days = (dates.max() - dates.min()).days
    if span_days > 365 * 2:
        freq, period_label = "MS", "month"
    elif span_days > 60:
        freq, period_label = "W", "week"
    else:
        freq, period_label = "D", "day"

    grouped = dates.dt.to_period(freq[0] if freq != "MS" else "M")
    counts = grouped.value_counts().sort_index()
    return {
        "column": str(col),
        "period": period_label,
        "labels": [str(p) for p in counts.index.astype(str).tolist()],
        "counts": [int(c) for c in counts.tolist()],
    }


def analyze_dataframe(df: pd.DataFrame, filename: str = "data.csv") -> dict[str, Any]:
    """Produce the full report dictionary for an already-loaded DataFrame."""
    if df.empty:
        raise ValueError("The uploaded file has no rows to analyse.")

    df = _detect_datetime(df)

    rows, cols = df.shape
    missing_cells = int(df.isna().sum().sum())
    total_cells = rows * cols
    profiles = _column_profiles(df)

    return {
        "filename": filename,
        "overview": {
            "rows": int(rows),
            "columns": int(cols),
            "numeric_columns": sum(1 for p in profiles if p["dtype"] == "numeric"),
            "text_columns": sum(1 for p in profiles if p["dtype"] == "text"),
            "datetime_columns": sum(1 for p in profiles if p["dtype"] == "datetime"),
            "missing_cells": missing_cells,
            "missing_pct": round((missing_cells / total_cells) * 100, 1)
            if total_cells
            else 0.0,
            "duplicate_rows": int(df.duplicated().sum()),
        },
        "columns": profiles,
        "numeric_summary": _numeric_summary(df),
        "categorical_summary": _categorical_summary(df),
        "histograms": _numeric_histograms(df),
        "time_series": _time_series(df),
        "preview": _preview(df),
    }


def _preview(df: pd.DataFrame, rows: int = 8) -> dict[str, Any]:
    head = df.head(rows).copy()
    # Stringify datetimes / NaNs so the dict is cleanly JSON-serialisable.
    for col in head.columns:
        if pd.api.types.is_datetime64_any_dtype(head[col]):
            head[col] = head[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    head = head.where(pd.notna(head), None)
    return {
        "headers": [str(c) for c in head.columns],
        "rows": head.astype(object).values.tolist(),
    }


def analyze_csv(file_or_path: Any, filename: str = "data.csv") -> dict[str, Any]:
    """Read a CSV from a path or file-like object and build the report."""
    try:
        df = pd.read_csv(file_or_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The uploaded file is empty.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Could not parse the CSV file: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The file is not valid UTF-8 text. Please upload a UTF-8 CSV."
        ) from exc
    return analyze_dataframe(df, filename=filename)
