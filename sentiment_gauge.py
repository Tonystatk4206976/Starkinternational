"""Plotly gauge helper for visualizing market sentiment."""

from __future__ import annotations

import plotly.graph_objects as go


def display_sentiment_gauge(score: float, *, compact: bool = False) -> go.Figure:
    """Build a Plotly gauge that maps sentiment from [-1.0, 1.0] to [0, 100].

    Args:
        score: Sentiment score where -1.0 means extreme fear and +1.0 means
            extreme greed.
        compact: When True, renders a tighter layout for denser dashboard UIs.

    Returns:
        A Plotly figure configured as a sentiment gauge.
    """
    clipped_score = max(-1.0, min(1.0, float(score)))
    display_value = (clipped_score + 1) * 50

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=display_value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Market Sentiment Index", "font": {"size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "black"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 30], "color": "red"},
                    {"range": [30, 45], "color": "orange"},
                    {"range": [45, 55], "color": "yellow"},
                    {"range": [55, 70], "color": "lightgreen"},
                    {"range": [70, 100], "color": "green"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        )
    )
    sentiment_label = (
        "Extreme Fear" if clipped_score <= -0.6
        else "Fear" if clipped_score <= -0.2
        else "Neutral" if clipped_score < 0.2
        else "Greed" if clipped_score < 0.6
        else "Extreme Greed"
    )

    height = 220 if compact else 300
    number_font_size = 22 if compact else 30
    title_size = 18 if compact else 24
    fig.update_traces(
        number={"suffix": "%", "font": {"size": number_font_size}},
        title={"text": f"Market Sentiment Index • {sentiment_label}", "font": {"size": title_size}},
    )
    fig.update_layout(height=height, margin=dict(l=14, r=14, t=40, b=14 if compact else 20))
    return fig


# Example Streamlit usage:
# score = calculate_greed_score(headlines)
# st.plotly_chart(display_sentiment_gauge(score), use_container_width=True)
