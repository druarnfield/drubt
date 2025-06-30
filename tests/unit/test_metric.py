"""Unit tests for Metric model."""

import pytest
from datetime import datetime

from dbt_metrics_manager.models import Metric


def test_metric_creation():
    """Test basic metric creation."""
    metric = Metric(
        metric_category="emergency",
        name="ED Presentations",
        short="ED_PRES",
        type="direct",
        value="presentations_value"
    )
    
    assert metric.name == "ED Presentations"
    assert metric.short == "ED_PRES"
    assert metric.type == "direct"
    assert metric.value == "presentations_value"
    assert metric.created_at is not None
    assert metric.updated_at is not None


def test_metric_validation_direct():
    """Test validation for direct metrics."""
    # Valid direct metric
    metric = Metric(
        metric_category="emergency",
        name="ED Presentations",
        short="ED_PRES",
        type="direct",
        value="presentations_value"
    )
    errors = metric.validate()
    assert len(errors) == 0
    
    # Invalid direct metric (missing value)
    metric_invalid = Metric(
        metric_category="emergency",
        name="ED Presentations",
        short="ED_PRES",
        type="direct"
    )
    errors = metric_invalid.validate()
    assert "Direct metrics require a value column" in errors


def test_metric_validation_ratio():
    """Test validation for ratio metrics."""
    # Valid ratio metric
    metric = Metric(
        metric_category="emergency",
        name="ED LOS Rate",
        short="LOS_4HR",
        type="ratio",
        numerator="los_4hr_numerator",
        denominator="los_4hr_denominator"
    )
    errors = metric.validate()
    assert len(errors) == 0
    
    # Invalid ratio metric (missing denominator)
    metric_invalid = Metric(
        metric_category="emergency",
        name="ED LOS Rate",
        short="LOS_4HR",
        type="ratio",
        numerator="los_4hr_numerator"
    )
    errors = metric_invalid.validate()
    assert "Ratio metrics require numerator and denominator" in errors


def test_metric_to_dict():
    """Test metric serialization to dictionary."""
    metric = Metric(
        metric_category="emergency",
        name="ED Presentations",
        short="ED_PRES",
        type="direct",
        value="presentations_value",
        description="Total ED presentations",
        tags=["emergency", "volume"]
    )
    
    data = metric.to_dict()
    
    assert data["name"] == "ED Presentations"
    assert data["short"] == "ED_PRES"
    assert data["type"] == "direct"
    assert data["value"] == "presentations_value"
    assert data["description"] == "Total ED presentations"
    assert data["tags"] == "emergency,volume"


def test_metric_from_dict():
    """Test metric creation from dictionary."""
    data = {
        "metric_category": "emergency",
        "name": "ED Presentations",
        "short": "ED_PRES",
        "type": "direct",
        "value": "presentations_value",
        "description": "Total ED presentations",
        "tags": "emergency,volume"
    }
    
    metric = Metric.from_dict(data)
    
    assert metric.name == "ED Presentations"
    assert metric.short == "ED_PRES"
    assert metric.type == "direct"
    assert metric.value == "presentations_value"
    assert metric.description == "Total ED presentations"
    assert metric.tags == ["emergency", "volume"]