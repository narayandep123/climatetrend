from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import requests

from backend.app.config import DEFAULT_REGIONS
from backend.app.db import get_database, now_iso

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_default_regions() -> List[Dict[str, Any]]:
    return DEFAULT_REGIONS


def search_regions(query: str) -> List[Dict[str, Any]]:
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "name": clean_query,
                "count": 8,
                "language": "en",
                "format": "json",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return []

    results: List[Dict[str, Any]] = []
    for item in payload.get("results", []):
        results.append(
            {
                "name": item.get("name"),
                "country": item.get("country"),
                "state": item.get("admin1") or item.get("admin2"),
                "latitude": _safe_float(item.get("latitude")),
                "longitude": _safe_float(item.get("longitude")),
            }
        )
    return results


def fetch_daily_temperature_series(latitude: float, longitude: float, start_year: int, end_year: int) -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            ARCHIVE_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": f"{start_year}-01-01",
                "end_date": f"{end_year}-12-31",
                "daily": "temperature_2m_max",
                "timezone": "auto",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return []

    if not isinstance(payload, dict):
        return []

    daily = payload.get("daily", {})
    if not isinstance(daily, dict):
        return []

    dates = daily.get("time", [])
    temperatures = daily.get("temperature_2m_max", [])

    series: List[Dict[str, Any]] = []
    for date_value, temp_value in zip(dates, temperatures):
        if temp_value is None:
            continue
        series.append({"date": date_value, "temp_c": _safe_float(temp_value)})
    return series


def _build_yearly_counts(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    yearly = defaultdict(int)
    yearly_duration = defaultdict(float)
    for event in events:
        year = event["start_date"][:4]
        yearly[year] += 1
        yearly_duration[year] += event["duration_days"]

    years = sorted({int(year) for year in yearly.keys()})
    result: List[Dict[str, Any]] = []
    for year in years:
        result.append(
            {
                "year": year,
                "event_count": yearly.get(str(year), 0),
                "average_duration_days": round(yearly_duration.get(str(year), 0) / max(yearly.get(str(year), 0), 1), 2),
            }
        )
    return result


def _calculate_regression_trend(yearly_counts: List[Dict[str, Any]]) -> Dict[str, float]:
    if len(yearly_counts) < 2:
        return {"slope": 0.0, "per_decade": 0.0, "trend_label": "Stable trend"}

    x = np.array([point["year"] for point in yearly_counts], dtype=float)
    y = np.array([point["event_count"] for point in yearly_counts], dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    per_decade = float(slope * 10)
    if slope > 0:
        label = "Increasing trend"
    elif slope < 0:
        label = "Declining trend"
    else:
        label = "Stable trend"
    return {"slope": slope, "per_decade": per_decade, "trend_label": label}


def detect_heatwaves(records: List[Dict[str, Any]], threshold_c: float) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    current_run: List[Dict[str, Any]] = []

    for record in records:
        temp_c = record["temp_c"]
        if temp_c >= threshold_c:
            current_run.append(record)
            continue

        if len(current_run) >= 3:
            peak_temp = max(item["temp_c"] for item in current_run)
            mean_temp = sum(item["temp_c"] for item in current_run) / len(current_run)
            events.append(
                {
                    "start_date": current_run[0]["date"],
                    "end_date": current_run[-1]["date"],
                    "duration_days": len(current_run),
                    "peak_temp_c": round(peak_temp, 2),
                    "mean_temp_c": round(mean_temp, 2),
                }
            )
        current_run = []

    if len(current_run) >= 3:
        peak_temp = max(item["temp_c"] for item in current_run)
        mean_temp = sum(item["temp_c"] for item in current_run) / len(current_run)
        events.append(
            {
                "start_date": current_run[0]["date"],
                "end_date": current_run[-1]["date"],
                "duration_days": len(current_run),
                "peak_temp_c": round(peak_temp, 2),
                "mean_temp_c": round(mean_temp, 2),
            }
        )

    return events


def fetch_daily_precipitation_series(latitude: float, longitude: float, start_year: int, end_year: int) -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            ARCHIVE_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": f"{start_year}-01-01",
                "end_date": f"{end_year}-12-31",
                "daily": "precipitation_sum",
                "timezone": "auto",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return []

    if not isinstance(payload, dict):
        return []

    daily = payload.get("daily", {})
    if not isinstance(daily, dict):
        return []

    dates = daily.get("time", [])
    precipitation = daily.get("precipitation_sum", [])

    series: List[Dict[str, Any]] = []
    for date_value, precip_value in zip(dates, precipitation):
        if precip_value is None:
            continue
        series.append({"date": date_value, "precip_mm": _safe_float(precip_value)})
    return series


def detect_heavy_rainfall(records: List[Dict[str, Any]], threshold_mm: float) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    current_run: List[Dict[str, Any]] = []

    for record in records:
        precip_mm = record["precip_mm"]
        if precip_mm >= threshold_mm:
            current_run.append(record)
            continue

        if len(current_run) >= 2:
            peak_precip = max(item["precip_mm"] for item in current_run)
            total_precip = sum(item["precip_mm"] for item in current_run)
            events.append(
                {
                    "start_date": current_run[0]["date"],
                    "end_date": current_run[-1]["date"],
                    "duration_days": len(current_run),
                    "peak_precip_mm": round(peak_precip, 2),
                    "total_precip_mm": round(total_precip, 2),
                }
            )
        current_run = []

    if len(current_run) >= 2:
        peak_precip = max(item["precip_mm"] for item in current_run)
        total_precip = sum(item["precip_mm"] for item in current_run)
        events.append(
            {
                "start_date": current_run[0]["date"],
                "end_date": current_run[-1]["date"],
                "duration_days": len(current_run),
                "peak_precip_mm": round(peak_precip, 2),
                "total_precip_mm": round(total_precip, 2),
            }
        )

    return events


def detect_droughts(records: List[Dict[str, Any]], threshold_mm: float) -> List[Dict[str, Any]]:
    annual_totals: Dict[str, float] = defaultdict(float)
    for record in records:
        year = record["date"][:4]
        annual_totals[year] += record["precip_mm"]

    years = sorted(annual_totals.keys())
    if not years:
        return []

    threshold = float(np.percentile(list(annual_totals.values()), 25))
    events: List[Dict[str, Any]] = []
    for year in years:
        if annual_totals[year] < threshold:
            events.append(
                {
                    "start_date": f"{year}-01-01",
                    "end_date": f"{year}-12-31",
                    "duration_days": 365,
                    "annual_precip_mm": round(annual_totals[year], 2),
                    "threshold_mm": round(threshold, 2),
                }
            )
    return events


def _build_summary_text(region_name: str, events: List[Dict[str, Any]], trend: Dict[str, float], threshold_c: float, hazard: str) -> str:
    if not events:
        if hazard == "heatwave":
            return f"No sustained heatwaves were detected for {region_name} during the selected period. Climate risk remains modest relative to the percentile rule used here."
        if hazard == "drought":
            return f"No sustained drought conditions were detected for {region_name}. Rainfall remained relatively resilient compared with the local baseline."
        return f"No sustained heavy rainfall episodes were detected for {region_name}. Extremes remained limited relative to the local precipitation baseline."

    total_events = len(events)
    mean_duration = round(sum(item["duration_days"] for item in events) / total_events, 2)
    change = trend["per_decade"]
    direction = "increasing" if change > 0 else "declining" if change < 0 else "stable"

    if hazard == "heatwave":
        if change > 0:
            return (
                f"Heatwaves have become {direction} in {region_name} since the study window began, with {total_events} events "
                f"of average duration {mean_duration} days and a threshold of {threshold_c:.1f}°C. The pattern points to a higher number of heat exceedance episodes in later years."
            )
        if change < 0:
            return (
                f"Heatwaves have become {direction} in {region_name} since the study window began, with {total_events} events "
                f"of average duration {mean_duration} days and a threshold of {threshold_c:.1f}°C. The recent pattern shows fewer exceedance episodes over time, even though individual events can remain intense."
            )
        return (
            f"Heatwaves have remained comparatively {direction} in {region_name} during the selected period, with {total_events} events "
            f"of average duration {mean_duration} days and a threshold of {threshold_c:.1f}°C. The annual pattern stays broadly consistent over time."
        )

    if hazard == "drought":
        if change > 0:
            return (
                f"Dry conditions have become {direction} in {region_name}, with {total_events} low-rainfall years and a threshold of {threshold_c:.1f} mm annual rainfall. The recent pattern suggests increasingly water-stressed conditions."
            )
        if change < 0:
            return (
                f"Dry conditions have become {direction} in {region_name}, with {total_events} low-rainfall years and a threshold of {threshold_c:.1f} mm annual rainfall. Rainfall deficits are becoming less severe in the recent record."
            )
        return (
            f"Dry conditions have remained comparatively {direction} in {region_name}, with {total_events} low-rainfall years and a threshold of {threshold_c:.1f} mm annual rainfall. The period remains broadly stable in rainfall stress."
        )

    if change > 0:
        return (
            f"Heavy rainfall episodes have become {direction} in {region_name}, with {total_events} episodes of average duration {mean_duration} days and a threshold of {threshold_c:.1f} mm. The signal points to more intense wet extremes in later years."
        )
    if change < 0:
        return (
            f"Heavy rainfall episodes have become {direction} in {region_name}, with {total_events} episodes of average duration {mean_duration} days and a threshold of {threshold_c:.1f} mm. Wet extremes appear less frequent in the later record."
        )
    return (
        f"Heavy rainfall episodes have remained comparatively {direction} in {region_name}, with {total_events} episodes of average duration {mean_duration} days and a threshold of {threshold_c:.1f} mm. The wet-extreme pattern stays broadly stable."
    )


def analyze_climate_hazard(hazard: str, region_name: str, latitude: float, longitude: float, start_year: int, end_year: int) -> Dict[str, Any]:
    if hazard == "drought":
        return analyze_drought(region_name, latitude, longitude, start_year, end_year)
    if hazard == "heavy_rainfall":
        return analyze_heavy_rainfall(region_name, latitude, longitude, start_year, end_year)
    return analyze_heatwave(region_name, latitude, longitude, start_year, end_year)


def analyze_heatwave(region_name: str, latitude: float, longitude: float, start_year: int, end_year: int) -> Dict[str, Any]:
    cache = get_database()
    cache_key = f"heatwave::{region_name}::{float(latitude)}::{float(longitude)}::{start_year}::{end_year}"
    cached = cache.weather_cache.find_one({"cache_key": cache_key})
    if cached and cached.get("updated_at"):
        cached_age_days = (datetime.utcnow() - datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))).days
        if cached_age_days < 7:
            return cached["result"]

    records = fetch_daily_temperature_series(latitude, longitude, start_year, end_year)
    if not records:
        return {
            "region_name": region_name,
            "hazard": "heatwave",
            "summary": "No valid temperature data was returned from the source API for the selected location.",
            "chart_data": [],
            "events": [],
            "threshold_c": 0.0,
            "signal": "insufficient-data",
        }

    temps = [record["temp_c"] for record in records]
    threshold_c = float(np.percentile(temps, 95))
    events = detect_heatwaves(records, threshold_c)
    yearly_data = _build_yearly_counts(events)
    trend = _calculate_regression_trend(yearly_data)

    if yearly_data:
        first_count = yearly_data[0]["event_count"]
        final_count = yearly_data[-1]["event_count"]
        percent_change = 0.0 if first_count == 0 else round(((final_count - first_count) / first_count) * 100, 1)
    else:
        percent_change = 0.0

    summary = {
        "region_name": region_name,
        "hazard": "heatwave",
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start_year": start_year,
        "end_year": end_year,
        "threshold_c": round(threshold_c, 2),
        "total_event_count": len(events),
        "average_duration_days": round(sum(item["duration_days"] for item in events) / max(len(events), 1), 2),
        "percent_change_from_start": percent_change,
        "trend_per_decade": round(trend["per_decade"], 2),
        "trend_label": trend["trend_label"],
        "insight": _build_summary_text(region_name, events, trend, threshold_c, "heatwave"),
        "chart_data": yearly_data,
        "events": events,
        "signal": "heatwave-detected" if events else "no-heatwaves",
    }

    result = {
        "region_name": region_name,
        "hazard": "heatwave",
        "summary": summary,
        "chart_data": yearly_data,
        "events": events,
        "threshold_c": round(threshold_c, 2),
        "insight": summary["insight"],
        "signal": summary["signal"],
    }

    cache.weather_cache.update_one(
        {"cache_key": cache_key},
        {
            "$set": {
                "cache_key": cache_key,
                "region_name": region_name,
                "latitude": latitude,
                "longitude": longitude,
                "start_year": start_year,
                "end_year": end_year,
                "hazard": "heatwave",
                "result": result,
                "updated_at": now_iso(),
            }
        },
        upsert=True,
    )
    return result


def analyze_drought(region_name: str, latitude: float, longitude: float, start_year: int, end_year: int) -> Dict[str, Any]:
    cache = get_database()
    cache_key = f"drought::{region_name}::{float(latitude)}::{float(longitude)}::{start_year}::{end_year}"
    cached = cache.weather_cache.find_one({"cache_key": cache_key})
    if cached and cached.get("updated_at"):
        cached_age_days = (datetime.utcnow() - datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))).days
        if cached_age_days < 7:
            return cached["result"]

    records = fetch_daily_precipitation_series(latitude, longitude, start_year, end_year)
    if not records:
        return {
            "region_name": region_name,
            "hazard": "drought",
            "summary": "No valid precipitation data was returned from the source API for the selected location.",
            "chart_data": [],
            "events": [],
            "threshold_c": 0.0,
            "signal": "insufficient-data",
        }

    annual_totals = defaultdict(float)
    for record in records:
        annual_totals[record["date"][:4]] += record["precip_mm"]

    yearly_data = [
        {"year": int(year), "event_count": 1 if total < float(np.percentile(list(annual_totals.values()), 25)) else 0, "average_duration_days": 1 if total < float(np.percentile(list(annual_totals.values()), 25)) else 0}
        for year, total in annual_totals.items()
    ]
    yearly_data.sort(key=lambda item: item["year"])
    trend = _calculate_regression_trend(yearly_data)
    threshold_mm = float(np.percentile(list(annual_totals.values()), 25))
    events = detect_droughts(records, threshold_mm)

    if yearly_data:
        first_count = yearly_data[0]["event_count"]
        final_count = yearly_data[-1]["event_count"]
        percent_change = 0.0 if first_count == 0 else round(((final_count - first_count) / first_count) * 100, 1)
    else:
        percent_change = 0.0

    summary = {
        "region_name": region_name,
        "hazard": "drought",
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start_year": start_year,
        "end_year": end_year,
        "threshold_c": round(threshold_mm, 2),
        "total_event_count": len(events),
        "average_duration_days": round(sum(item["duration_days"] for item in events) / max(len(events), 1), 2),
        "percent_change_from_start": percent_change,
        "trend_per_decade": round(trend["per_decade"], 2),
        "trend_label": trend["trend_label"],
        "insight": _build_summary_text(region_name, events, trend, threshold_mm, "drought"),
        "chart_data": yearly_data,
        "events": events,
        "signal": "drought-detected" if events else "no-drought",
    }

    result = {
        "region_name": region_name,
        "hazard": "drought",
        "summary": summary,
        "chart_data": yearly_data,
        "events": events,
        "threshold_c": round(threshold_mm, 2),
        "insight": summary["insight"],
        "signal": summary["signal"],
    }

    cache.weather_cache.update_one(
        {"cache_key": cache_key},
        {"$set": {"cache_key": cache_key, "region_name": region_name, "latitude": latitude, "longitude": longitude, "start_year": start_year, "end_year": end_year, "hazard": "drought", "result": result, "updated_at": now_iso()}},
        upsert=True,
    )
    return result


def analyze_heavy_rainfall(region_name: str, latitude: float, longitude: float, start_year: int, end_year: int) -> Dict[str, Any]:
    cache = get_database()
    cache_key = f"heavy_rainfall::{region_name}::{float(latitude)}::{float(longitude)}::{start_year}::{end_year}"
    cached = cache.weather_cache.find_one({"cache_key": cache_key})
    if cached and cached.get("updated_at"):
        cached_age_days = (datetime.utcnow() - datetime.fromisoformat(cached["updated_at"].replace("Z", "+00:00"))).days
        if cached_age_days < 7:
            return cached["result"]

    records = fetch_daily_precipitation_series(latitude, longitude, start_year, end_year)
    if not records:
        return {
            "region_name": region_name,
            "hazard": "heavy_rainfall",
            "summary": "No valid precipitation data was returned from the source API for the selected location.",
            "chart_data": [],
            "events": [],
            "threshold_c": 0.0,
            "signal": "insufficient-data",
        }

    precip_values = [item["precip_mm"] for item in records]
    threshold_mm = float(np.percentile(precip_values, 95))
    events = detect_heavy_rainfall(records, threshold_mm)
    yearly_data = _build_yearly_counts(events)
    trend = _calculate_regression_trend(yearly_data)

    if yearly_data:
        first_count = yearly_data[0]["event_count"]
        final_count = yearly_data[-1]["event_count"]
        percent_change = 0.0 if first_count == 0 else round(((final_count - first_count) / first_count) * 100, 1)
    else:
        percent_change = 0.0

    summary = {
        "region_name": region_name,
        "hazard": "heavy_rainfall",
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start_year": start_year,
        "end_year": end_year,
        "threshold_c": round(threshold_mm, 2),
        "total_event_count": len(events),
        "average_duration_days": round(sum(item["duration_days"] for item in events) / max(len(events), 1), 2),
        "percent_change_from_start": percent_change,
        "trend_per_decade": round(trend["per_decade"], 2),
        "trend_label": trend["trend_label"],
        "insight": _build_summary_text(region_name, events, trend, threshold_mm, "heavy_rainfall"),
        "chart_data": yearly_data,
        "events": events,
        "signal": "heavy-rainfall-detected" if events else "no-heavy-rainfall",
    }

    result = {
        "region_name": region_name,
        "hazard": "heavy_rainfall",
        "summary": summary,
        "chart_data": yearly_data,
        "events": events,
        "threshold_c": round(threshold_mm, 2),
        "insight": summary["insight"],
        "signal": summary["signal"],
    }

    cache.weather_cache.update_one(
        {"cache_key": cache_key},
        {"$set": {"cache_key": cache_key, "region_name": region_name, "latitude": latitude, "longitude": longitude, "start_year": start_year, "end_year": end_year, "hazard": "heavy_rainfall", "result": result, "updated_at": now_iso()}},
        upsert=True,
    )
    return result
