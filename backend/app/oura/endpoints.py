"""Oura API v2 endpoint definitions.

Reference: https://cloud.ouraring.com/v2/docs
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class EndpointConfig:
    """Configuration for an Oura API endpoint."""
    path: str
    date_param_type: Literal["date", "datetime", None] = "date"
    paginated: bool = True
    id_field: str = "id"  # Field name for record ID in response


# All Oura v2 endpoints we support
OURA_ENDPOINTS: dict[str, EndpointConfig] = {
    # Non-paginated, no date filtering
    "personal_info": EndpointConfig(
        path="/v2/usercollection/personal_info",
        date_param_type=None,
        paginated=False,
    ),
    # Daily summaries (date range with start_date/end_date)
    "daily_sleep": EndpointConfig(
        path="/v2/usercollection/daily_sleep",
        date_param_type="date",
        paginated=True,
    ),
    "daily_readiness": EndpointConfig(
        path="/v2/usercollection/daily_readiness",
        date_param_type="date",
        paginated=True,
    ),
    "daily_activity": EndpointConfig(
        path="/v2/usercollection/daily_activity",
        date_param_type="date",
        paginated=True,
    ),
    "daily_spo2": EndpointConfig(
        path="/v2/usercollection/daily_spo2",
        date_param_type="date",
        paginated=True,
    ),
    "daily_stress": EndpointConfig(
        path="/v2/usercollection/daily_stress",
        date_param_type="date",
        paginated=True,
    ),
    # Granular data (date range with start_date/end_date)
    "sleep": EndpointConfig(
        path="/v2/usercollection/sleep",
        date_param_type="date",
        paginated=True,
    ),
    "workout": EndpointConfig(
        path="/v2/usercollection/workout",
        date_param_type="date",
        paginated=True,
    ),
    "session": EndpointConfig(
        path="/v2/usercollection/session",
        date_param_type="date",
        paginated=True,
    ),
    "tag": EndpointConfig(
        path="/v2/usercollection/tag",
        date_param_type="date",
        paginated=True,
    ),
    "enhanced_tag": EndpointConfig(
        path="/v2/usercollection/enhanced_tag",
        date_param_type="date",
        paginated=True,
    ),
    # Time-series data (datetime range with start_datetime/end_datetime)
    "heartrate": EndpointConfig(
        path="/v2/usercollection/heartrate",
        date_param_type="datetime",
        paginated=True,
    ),
    # Configuration endpoints
    "ring_configuration": EndpointConfig(
        path="/v2/usercollection/ring_configuration",
        date_param_type="date",
        paginated=True,
    ),
    "rest_mode_period": EndpointConfig(
        path="/v2/usercollection/rest_mode_period",
        date_param_type="date",
        paginated=True,
    ),
    "sleep_time": EndpointConfig(
        path="/v2/usercollection/sleep_time",
        date_param_type="date",
        paginated=True,
    ),
}

# Endpoints to include in default backfill (ordered)
BACKFILL_ENDPOINTS: list[str] = [
    "personal_info",
    "daily_sleep",
    "daily_readiness",
    "daily_activity",
    "daily_spo2",
    "daily_stress",
    "sleep",
    "workout",
    "session",
]


def get_endpoint_config(endpoint_name: str) -> EndpointConfig:
    """Get configuration for a specific endpoint."""
    if endpoint_name not in OURA_ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint_name}. Available: {list(OURA_ENDPOINTS.keys())}")
    return OURA_ENDPOINTS[endpoint_name]
