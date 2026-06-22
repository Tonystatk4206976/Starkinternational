import importlib
import math
import sys
import types

import pytest


class FakeIndicator:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeFigure:
    def __init__(self, indicator):
        self.indicator = indicator
        self.layout_updates = {}

    def update_layout(self, **kwargs):
        self.layout_updates.update(kwargs)


class FakeGraphObjects(types.ModuleType):
    Indicator = FakeIndicator
    Figure = FakeFigure


def import_with_fake_plotly(monkeypatch):
    fake_plotly = types.ModuleType("plotly")
    fake_graph_objects = FakeGraphObjects("plotly.graph_objects")
    fake_plotly.graph_objects = fake_graph_objects
    monkeypatch.setitem(sys.modules, "plotly", fake_plotly)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_graph_objects)
    sys.modules.pop("sentiment_gauge", None)
    return importlib.import_module("sentiment_gauge")


def test_sentiment_score_helpers_clamp_and_describe_scores(monkeypatch):
    sentiment_gauge = import_with_fake_plotly(monkeypatch)

    assert sentiment_gauge.clamp_sentiment_score(3) == 1
    assert sentiment_gauge.sentiment_score_to_index(-1) == 0
    assert sentiment_gauge.sentiment_score_to_index(0) == 50
    assert sentiment_gauge.sentiment_score_to_index(1) == 100
    assert sentiment_gauge.describe_sentiment(-0.8) == "Extreme Fear"
    assert sentiment_gauge.describe_sentiment(0) == "Neutral"
    assert sentiment_gauge.describe_sentiment(0.8) == "Extreme Greed"


def test_sentiment_score_helpers_reject_invalid_scores(monkeypatch):
    sentiment_gauge = import_with_fake_plotly(monkeypatch)

    with pytest.raises(TypeError, match="score must be numeric"):
        sentiment_gauge.clamp_sentiment_score(True)

    with pytest.raises(TypeError, match="score must be numeric"):
        sentiment_gauge.clamp_sentiment_score("not-a-score")

    with pytest.raises(ValueError, match="score must be finite"):
        sentiment_gauge.clamp_sentiment_score(math.nan)

    with pytest.raises(ValueError, match="score must be finite"):
        sentiment_gauge.display_sentiment_gauge(math.inf)


def test_build_sentiment_steps_returns_fresh_plotly_step_dicts(monkeypatch):
    sentiment_gauge = import_with_fake_plotly(monkeypatch)

    first = sentiment_gauge.build_sentiment_steps()
    second = sentiment_gauge.build_sentiment_steps()

    assert first == second == sentiment_gauge.SENTIMENT_STEPS
    assert first is not second
    assert first is not sentiment_gauge.SENTIMENT_STEPS
    assert first[0] is not second[0]


def test_standard_gauge_preserves_original_title_by_default(monkeypatch):
    sentiment_gauge = import_with_fake_plotly(monkeypatch)

    fig = sentiment_gauge.display_sentiment_gauge(0.7)

    assert fig.indicator.kwargs["title"] == {
        "text": "Market Sentiment Index",
        "font": {"size": 24},
    }
    assert fig.layout_updates == {
        "height": 300,
        "margin": {"l": 20, "r": 20, "t": 50, "b": 20},
    }


def test_compact_gauge_uses_tighter_layout_and_inline_label(monkeypatch):
    sentiment_gauge = import_with_fake_plotly(monkeypatch)

    fig = sentiment_gauge.display_sentiment_gauge(0.7, compact=True)

    assert fig.indicator.kwargs["value"] == 85
    assert fig.indicator.kwargs["title"] == {
        "text": "Market Sentiment Index • Extreme Greed",
        "font": {"size": 18},
    }
    assert fig.indicator.kwargs["number"] == {"valueformat": ".0f", "font": {"size": 22}}
    assert fig.layout_updates == {
        "height": 220,
        "margin": {"l": 14, "r": 14, "t": 40, "b": 14},
    }


def test_gauge_label_can_be_overridden(monkeypatch):
    sentiment_gauge = import_with_fake_plotly(monkeypatch)

    hidden = sentiment_gauge.display_sentiment_gauge(
        -0.7,
        compact=True,
        show_label=False,
    )
    visible = sentiment_gauge.display_sentiment_gauge(
        -0.7,
        compact=False,
        show_label=True,
    )

    assert hidden.indicator.kwargs["title"]["text"] == "Market Sentiment Index"
    assert visible.indicator.kwargs["title"]["text"] == "Market Sentiment Index • Extreme Fear"
