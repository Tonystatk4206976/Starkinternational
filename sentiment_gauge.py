"""Plotly gauge helper for visualizing market sentiment."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import plotly.graph_objects as go

_SENTIMENT_STEPS = [
    {"range": [0, 30], "color": "#d73027"},
    {"range": [30, 45], "color": "#fc8d59"},
    {"range": [45, 55], "color": "#fee08b"},
    {"range": [55, 70], "color": "#91cf60"},
    {"range": [70, 100], "color": "#1a9850"},
]

_SENTIMENT_BANDS = [
    (-0.6, "Extreme Fear"),
    (-0.2, "Fear"),
    (0.2, "Neutral"),
    (0.6, "Greed"),
    (math.inf, "Extreme Greed"),
]

_GAUGE_LAYOUTS = {
    False: {
        "height": 300,
        "margin": {"l": 20, "r": 20, "t": 50, "b": 20},
        "title_size": 24,
        "number_size": 30,
    },
    True: {
        "height": 220,
        "margin": {"l": 12, "r": 12, "t": 34, "b": 8},
        "title_size": 16,
        "number_size": 22,
    },
}


def sentiment_score_to_display_value(score: float) -> float:
    """Normalize a finite sentiment score from [-1.0, 1.0] to [0, 100]."""
    score_value = float(score)
    if not math.isfinite(score_value):
        raise ValueError("score must be a finite number")

    clipped_score = max(-1.0, min(1.0, score_value))
    return (clipped_score + 1.0) * 50.0


def describe_sentiment(score: float) -> str:
    """Return a concise label for a sentiment score."""
    score_value = float(score)
    if not math.isfinite(score_value):
        raise ValueError("score must be a finite number")

    clipped_score = max(-1.0, min(1.0, score_value))
    for upper_bound, label in _SENTIMENT_BANDS:
        if clipped_score <= upper_bound:
            return label

    return "Neutral"


def display_sentiment_gauge(score: float, *, compact: bool = False) -> "go.Figure":
    """Build a Plotly gauge that maps sentiment from [-1.0, 1.0] to [0, 100].

    Args:
        score: Sentiment score where -1.0 means extreme fear and +1.0 means
            extreme greed.
        compact: When True, renders a tighter layout for dense dashboard UIs.

    Returns:
        A Plotly figure configured as a sentiment gauge.
    """
    import plotly.graph_objects as go

    display_value = sentiment_score_to_display_value(score)
    sentiment_label = describe_sentiment(score)
    layout = _GAUGE_LAYOUTS[compact]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=display_value,
            domain={"x": [0, 1], "y": [0, 1]},
            number={"suffix": "%", "font": {"size": layout["number_size"]}},
            title={
                "text": f"Market Sentiment Index • {sentiment_label}",
                "font": {"size": layout["title_size"]},
            },
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#1f3a5f"},
                "bar": {"color": "#111827", "thickness": 0.28},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "#d1d5db",
                "steps": _SENTIMENT_STEPS,
                "threshold": {
                    "line": {"color": "#111827", "width": 3},
                    "thickness": 0.75,
                    "value": display_value,
                },
            },
        )
    )
    fig.update_layout(height=layout["height"], margin=layout["margin"])
    return fig


# Example Streamlit usage:
# score = calculate_greed_score(headlines)
# st.plotly_chart(display_sentiment_gauge(score, compact=True), use_container_width=True)
