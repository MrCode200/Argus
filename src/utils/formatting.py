"""Formatting utilities for display and output."""


def format_delta(change: float, symbol: str, decimal: int) -> str:
    """
    Format a delta value with color coding and directional arrow.

    Args:
        change: The change value to format.
        symbol: Unit symbol to append.
        decimal: Number of decimal places.

    Returns:
        Rich-formatted string with color (green for increase, red for decrease).
    """
    change = round(change, decimal)
    if change > 0:
        return f"[green]↑ +{change:.{decimal}f}{symbol}[/green]"
    elif change < 0:
        return f"[red]↓ {change:.{decimal}f}{symbol}[/red]"
    else:
        return f"[dim]→ 0{symbol}[/dim]"