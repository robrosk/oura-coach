"""Oura API v2 HTTP client with pagination support."""

from datetime import date, datetime
from typing import Any, Optional

import httpx

from ..core.config import get_settings
from ..core.logging import logger
from .endpoints import EndpointConfig, get_endpoint_config

settings = get_settings()


class OuraAPIError(Exception):
    """Oura API request errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class OuraClient:
    """HTTP client for Oura API v2 with automatic pagination."""

    def __init__(self, access_token: str):
        """Initialize client with access token.

        Args:
            access_token: Valid Oura API access token.
        """
        self.access_token = access_token
        self.base_url = settings.oura_api_base_url

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        endpoint_config: EndpointConfig,
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        """Make a single API request.

        Args:
            endpoint_config: Endpoint configuration.
            params: Query parameters.

        Returns:
            JSON response data.

        Raises:
            OuraAPIError: If request fails.
        """
        url = f"{self.base_url}{endpoint_config.path}"
        params = params or {}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=30.0,
                )

                if response.status_code == 401:
                    raise OuraAPIError("Access token expired or invalid", status_code=401)

                if response.status_code == 429:
                    raise OuraAPIError("Rate limit exceeded", status_code=429)

                if response.status_code != 200:
                    raise OuraAPIError(
                        f"API request failed: {response.status_code} - {response.text}",
                        status_code=response.status_code,
                    )

                return response.json()

            except httpx.RequestError as e:
                logger.error(f"Oura API request failed: {e}")
                raise OuraAPIError(f"Request failed: {e}")

    def _build_date_params(
        self,
        endpoint_config: EndpointConfig,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, str]:
        """Build date/datetime query parameters for an endpoint.

        Args:
            endpoint_config: Endpoint configuration.
            start_date: Start date for range.
            end_date: End date for range.

        Returns:
            Dict of query parameters.
        """
        params = {}

        if endpoint_config.date_param_type == "date":
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
        elif endpoint_config.date_param_type == "datetime":
            # For datetime endpoints, convert dates to datetime strings
            if start_date:
                params["start_datetime"] = datetime.combine(start_date, datetime.min.time()).isoformat()
            if end_date:
                params["end_datetime"] = datetime.combine(end_date, datetime.max.time()).isoformat()

        return params

    async def get_collection(
        self,
        endpoint_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Fetch all items from a paginated endpoint.

        Args:
            endpoint_name: Name of the endpoint (e.g., "daily_sleep").
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            List of all items from the endpoint.
        """
        endpoint_config = get_endpoint_config(endpoint_name)
        params = self._build_date_params(endpoint_config, start_date, end_date)

        if not endpoint_config.paginated:
            # Non-paginated endpoint - single request
            response = await self._request(endpoint_config, params)
            # personal_info returns a single object, wrap in list for consistency
            if isinstance(response, dict) and "data" not in response:
                return [response]
            return response.get("data", [])

        # Paginated endpoint - iterate through all pages
        items: list[dict] = []
        next_token: Optional[str] = None

        while True:
            if next_token:
                params["next_token"] = next_token

            response = await self._request(endpoint_config, params)

            data = response.get("data", [])
            items.extend(data)

            next_token = response.get("next_token")
            if not next_token:
                break

            logger.debug(f"Fetching next page for {endpoint_name} (got {len(items)} items so far)")

        logger.info(f"Fetched {len(items)} items from {endpoint_name}")
        return items

    async def get_personal_info(self) -> dict:
        """Fetch user's personal info.

        Returns:
            Personal info dict (id, age, weight, height, biological_sex, email).
        """
        items = await self.get_collection("personal_info")
        return items[0] if items else {}
