"""CoinGecko API client for cryptocurrency pricing.

This module provides a reusable CoinGecko client that:
- Automatically uses Pro API when API key is available
- Falls back to public API (with rate limits) without key
- Supports multiple currencies (JPY, USD, EUR, etc.)
- Caches responses for efficiency

Usage:
    from amplifier.crypto import get_prices, get_price

    # Get multiple coin prices
    prices = get_prices(["bitcoin", "ethereum", "sui"], currency="jpy")

    # Get single coin price
    btc = get_price("bitcoin", currency="usd")

Environment Variables:
    COINGECKO_API_KEY: Pro API key for higher rate limits
"""

import os
import time
from dataclasses import dataclass

import httpx


@dataclass
class CoinPrice:
    """Price data for a cryptocurrency."""

    id: str
    symbol: str
    name: str
    current_price: float
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap: float | None = None
    volume_24h: float | None = None


class CoinGeckoClient:
    """CoinGecko API client with automatic Pro/Public API selection."""

    PUBLIC_API = "https://api.coingecko.com/api/v3"
    PRO_API = "https://pro-api.coingecko.com/api/v3"

    # In-memory cache
    _cache: dict[str, tuple[float, any]] = {}
    CACHE_TTL = 300  # 5 minutes

    def __init__(self, api_key: str | None = None):
        """Initialize client with optional API key.

        Args:
            api_key: CoinGecko Pro API key. If not provided, uses
                     COINGECKO_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("COINGECKO_API_KEY")
        self.base_url = self.PRO_API if self.api_key else self.PUBLIC_API
        self.headers = {"x-cg-pro-api-key": self.api_key} if self.api_key else {}

    def _get_cached(self, key: str) -> any | None:
        """Get cached value if not expired."""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self.CACHE_TTL:
                return data
        return None

    def _set_cache(self, key: str, data: any) -> None:
        """Cache a value with timestamp."""
        self._cache[key] = (time.time(), data)

    def get_prices(self, coin_ids: list[str], currency: str = "usd") -> list[CoinPrice]:
        """Get current prices for multiple coins.

        Args:
            coin_ids: List of CoinGecko coin IDs (e.g., ["bitcoin", "ethereum"])
            currency: Target currency code (default: "usd")

        Returns:
            List of CoinPrice objects with current market data

        Raises:
            httpx.HTTPError: On API request failure
        """
        cache_key = f"prices:{','.join(sorted(coin_ids))}:{currency}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        ids = ",".join(coin_ids)
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": currency,
            "ids": ids,
            "order": "market_cap_desc",
            "sparkline": "false",
        }

        with httpx.Client() as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

        prices = [
            CoinPrice(
                id=coin["id"],
                symbol=coin["symbol"].upper(),
                name=coin["name"],
                current_price=coin["current_price"],
                price_change_24h=coin.get("price_change_24h", 0),
                price_change_percentage_24h=coin.get("price_change_percentage_24h", 0),
                market_cap=coin.get("market_cap"),
                volume_24h=coin.get("total_volume"),
            )
            for coin in data
        ]

        self._set_cache(cache_key, prices)
        return prices

    def get_price(self, coin_id: str, currency: str = "usd") -> CoinPrice:
        """Get current price for a single coin.

        Args:
            coin_id: CoinGecko coin ID (e.g., "bitcoin")
            currency: Target currency code (default: "usd")

        Returns:
            CoinPrice object with current market data

        Raises:
            ValueError: If coin not found
            httpx.HTTPError: On API request failure
        """
        prices = self.get_prices([coin_id], currency)
        if not prices:
            raise ValueError(f"Coin not found: {coin_id}")
        return prices[0]

    def get_historical_prices(
        self, coin_id: str, from_date: str, to_date: str | None = None, currency: str = "usd"
    ) -> list[dict]:
        """Get historical prices for a coin.

        Args:
            coin_id: CoinGecko coin ID
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD), defaults to today
            currency: Target currency code

        Returns:
            List of dicts with 'date' and 'price' keys
        """
        from datetime import datetime

        from_ts = int(datetime.fromisoformat(from_date).timestamp())
        to_ts = int(datetime.now().timestamp()) if not to_date else int(datetime.fromisoformat(to_date).timestamp())

        cache_key = f"history:{coin_id}:{from_date}:{to_date}:{currency}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{self.base_url}/coins/{coin_id}/market_chart/range"
        params = {
            "vs_currency": currency,
            "from": from_ts,
            "to": to_ts,
        }

        with httpx.Client() as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

        # Deduplicate by date
        prices_by_date: dict[str, float] = {}
        for timestamp, price in data.get("prices", []):
            date = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
            prices_by_date[date] = price

        result = [{"date": date, "price": price} for date, price in sorted(prices_by_date.items())]

        self._set_cache(cache_key, result)
        return result


# Module-level convenience functions using default client
_default_client: CoinGeckoClient | None = None


def _get_client() -> CoinGeckoClient:
    """Get or create the default client."""
    global _default_client
    if _default_client is None:
        _default_client = CoinGeckoClient()
    return _default_client


def get_prices(coin_ids: list[str], currency: str = "usd") -> list[CoinPrice]:
    """Get current prices for multiple coins using default client."""
    return _get_client().get_prices(coin_ids, currency)


def get_price(coin_id: str, currency: str = "usd") -> CoinPrice:
    """Get current price for a single coin using default client."""
    return _get_client().get_price(coin_id, currency)
