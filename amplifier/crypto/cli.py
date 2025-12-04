"""CLI for cryptocurrency pricing.

Usage:
    # From amplifier directory with make command
    make crypto-prices COINS=bitcoin,ethereum,sui CURRENCY=jpy

    # Or directly with uv
    uv run python -m amplifier.crypto bitcoin ethereum sui --currency jpy
"""

import click

from .coingecko import CoinGeckoClient
from .coingecko import CoinPrice


def format_price(price: CoinPrice, currency: str) -> str:
    """Format a price for display."""
    symbol = {"usd": "$", "jpy": "¥", "eur": "€"}.get(currency.lower(), "")
    change_color = "green" if price.price_change_percentage_24h >= 0 else "red"
    change_sign = "+" if price.price_change_percentage_24h >= 0 else ""

    return (
        f"{price.symbol:>6} │ {price.name:<12} │ "
        f"{symbol}{price.current_price:>14,.2f} │ "
        f"{change_sign}{price.price_change_percentage_24h:.2f}%"
    )


@click.command()
@click.argument("coins", nargs=-1, required=True)
@click.option("--currency", "-c", default="usd", help="Target currency (usd, jpy, eur, etc.)")
@click.option("--json", "-j", "as_json", is_flag=True, help="Output as JSON")
def main(coins: tuple[str, ...], currency: str, as_json: bool) -> None:
    """Get cryptocurrency prices from CoinGecko.

    COINS: One or more coin IDs (e.g., bitcoin ethereum sui)

    Examples:
        amplifier-crypto bitcoin ethereum sui
        amplifier-crypto bitcoin --currency jpy
        amplifier-crypto bitcoin ethereum --json
    """
    client = CoinGeckoClient()

    try:
        prices = client.get_prices(list(coins), currency)
    except Exception as e:
        click.echo(f"Error fetching prices: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        import json

        output = [
            {
                "id": p.id,
                "symbol": p.symbol,
                "name": p.name,
                "price": p.current_price,
                "change_24h": p.price_change_percentage_24h,
                "currency": currency,
            }
            for p in prices
        ]
        click.echo(json.dumps(output, indent=2))
    else:
        # Header
        click.echo("─" * 60)
        click.echo(f"{'Symbol':>6} │ {'Name':<12} │ {'Price':>15} │ {'24h':>8}")
        click.echo("─" * 60)

        # Prices
        for price in prices:
            click.echo(format_price(price, currency))

        click.echo("─" * 60)


if __name__ == "__main__":
    main()
