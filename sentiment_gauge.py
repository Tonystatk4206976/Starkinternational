"""Plotly gauge helper for visualizing market sentiment."""

from __future__ import annotations

import math
from dataclasses import dataclass

import plotly.graph_objects as go


@dataclass(frozen=True)
class GaugeLayoutPreset:
    """Spacing and typography settings for a sentiment gauge layout."""

    height: int
    title_size: int
    number_size: int
    margin: tuple[tuple[str, int], ...]


DEFAULT_GAUGE_LAYOUT = GaugeLayoutPreset(
    height=300,
    title_size=24,
    number_size=30,
    margin=(("l", 20), ("r", 20), ("t", 50), ("b", 20)),
)
COMPACT_GAUGE_LAYOUT = GaugeLayoutPreset(
    height=220,
    title_size=18,
    number_size=22,
    margin=(("l", 14), ("r", 14), ("t", 40), ("b", 14)),
)


_SENTIMENT_BANDS = (
    (0, 30, "red"),
    (30, 45, "orange"),
    (45, 55, "yellow"),
    (55, 70, "lightgreen"),
    (70, 100, "green"),
)


def build_sentiment_steps() -> list[dict[str, object]]:
    """Return fresh Plotly gauge color steps for the sentiment bands."""
    return [
        {"range": [lower_bound, upper_bound], "color": color}
        for lower_bound, upper_bound, color in _SENTIMENT_BANDS
    ]


SENTIMENT_STEPS = build_sentiment_steps()


def clamp_sentiment_score(score: float) -> float:
    """Clamp a finite raw sentiment score to the supported [-1.0, 1.0] range."""
    if isinstance(score, bool):
        raise TypeError("score must be numeric")
    try:
        numeric_score = float(score)
    except (TypeError, ValueError) as exc:
        raise TypeError("score must be numeric") from exc
    if not math.isfinite(numeric_score):
        raise ValueError("score must be finite")
    return max(-1.0, min(1.0, numeric_score))


def sentiment_score_to_index(score: float) -> float:
    """Map a sentiment score from [-1.0, 1.0] onto a 0-100 gauge index."""
    return (clamp_sentiment_score(score) + 1) * 50


def describe_sentiment(score: float) -> str:
    """Return a concise label for a raw sentiment score."""
    clipped_score = clamp_sentiment_score(score)
    if clipped_score <= -0.6:
        return "Extreme Fear"
    if clipped_score <= -0.2:
        return "Fear"
    if clipped_score < 0.2:
        return "Neutral"
    if clipped_score < 0.6:
        return "Greed"
    return "Extreme Greed"


def display_sentiment_gauge(
    score: float,
    *,
    compact: bool = False,
    show_label: bool | None = None,
) -> go.Figure:
    """Build a Plotly gauge that maps sentiment from [-1.0, 1.0] to [0, 100].

    Args:
        score: Sentiment score where -1.0 means extreme fear and +1.0 means
            extreme greed.
        compact: When True, renders a tighter layout for denser dashboard UIs.
        show_label: Controls whether the sentiment category is appended to the
            title. Defaults to matching `compact`, preserving the original title
            for the standard gauge while keeping dense dashboard gauges
            self-explanatory.

    Returns:
        A Plotly figure configured as a sentiment gauge.
    """
    clipped_score = clamp_sentiment_score(score)
    display_value = sentiment_score_to_index(clipped_score)
    preset = COMPACT_GAUGE_LAYOUT if compact else DEFAULT_GAUGE_LAYOUT
    should_show_label = compact if show_label is None else show_label
    title_text = "Market Sentiment Index"
    if should_show_label:
        title_text = f"{title_text} • {describe_sentiment(clipped_score)}"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=display_value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title_text, "font": {"size": preset.title_size}},
            number={"valueformat": ".0f", "font": {"size": preset.number_size}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "black"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": build_sentiment_steps(),
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        )
    )
    fig.update_layout(height=preset.height, margin=dict(preset.margin))
    return fig


# Example Streamlit usage:
# score = calculate_greed_score(headlines)
# st.plotly_chart(display_sentiment_gauge(score), use_container_width=True)
