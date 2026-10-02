import pytest

from datetime import date

from app.models.activity import Activity
from app.models.training_state import LoadTrend
from app.services.metrics import (
    calculate_activity_metrics,
    calculate_if,
    calculate_load_trend,
    calculate_tss,
    calculate_weekly_tss,
)

def test_calculate_if():
    result = calculate_if(
        normalized_power=200,
        ftp=250
    )

    assert result == 0.8

def test_calculate_tss():
    result = calculate_tss(
        duration_seconds=3600,
        normalized_power=200,
        ftp=250
    )

    assert result == 64

def test_calculate_weekly_tss():
    result = calculate_weekly_tss([64, 80, 45, 120])

    assert result == 309

def test_load_trend_increasing():
    result = calculate_load_trend(
        weekly_tss=350,
        previous_week_tss=300
    )

    assert result == LoadTrend.INCREASING

def test_load_trend_decreasing():
    result = calculate_load_trend(
        weekly_tss=250,
        previous_week_tss=300
    )

    assert result == LoadTrend.DECREASING

def test_load_trend_stable():
    result = calculate_load_trend(
        weekly_tss=300,
        previous_week_tss=300
    )

    assert result == LoadTrend.STABLE

def test_calculate_activity_metrics():
    activity = Activity(
        date=date(2026, 9, 16),
        duration_minutes=90,
        average_power=185,
        normalized_power=200,
    )

    result = calculate_activity_metrics(
        activity=activity, 
        ftp=250)

    assert activity.intensity_factor == 0.8
    assert activity.tss == 96
