import math

import pytest

from sentiment_gauge import describe_sentiment, sentiment_score_to_display_value


def test_sentiment_score_to_display_value_clips_range():
    assert sentiment_score_to_display_value(-2) == 0
    assert sentiment_score_to_display_value(0) == 50
    assert sentiment_score_to_display_value(2) == 100


def test_sentiment_helpers_reject_non_finite_scores():
    with pytest.raises(ValueError, match="finite"):
        sentiment_score_to_display_value(math.nan)

    with pytest.raises(ValueError, match="finite"):
        describe_sentiment(math.inf)


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (-0.8, "Extreme Fear"),
        (-0.4, "Fear"),
        (0, "Neutral"),
        (0.4, "Greed"),
        (0.8, "Extreme Greed"),
    ],
)
def test_describe_sentiment_returns_expected_label(score, label):
    assert describe_sentiment(score) == label


def test_display_sentiment_gauge_uses_compact_layout_when_plotly_is_available():
    pytest.importorskip("plotly")

    from sentiment_gauge import display_sentiment_gauge

    figure = display_sentiment_gauge(0.4, compact=True)

    assert figure.layout.height == 220
    assert "Greed" in figure.data[0].title.text
    assert figure.data[0].gauge.threshold.value == 70
