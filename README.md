# Starkinternational

Fund analytics helpers.

## Sentiment Gauge

This repo includes a Plotly helper to render a market sentiment gauge.

```python
from sentiment_gauge import display_sentiment_gauge

fig = display_sentiment_gauge(0.42)
fig.show()
```

For Streamlit:

```python
score = calculate_greed_score(headlines)
st.plotly_chart(display_sentiment_gauge(score), use_container_width=True)
```

## Semantic Similarity

Use `semantic_similarity` to compare two pieces of text, or
`rank_similar_texts` to find the closest matches in a list of headlines, notes,
or dashboard snippets without adding an external embedding dependency. The
helpers combine TF-IDF cosine scoring with a small default alias map for common
market synonyms, such as `shares`/`stocks` and `rally`/`rise`.

```python
from semantic_similarity import rank_similar_texts, semantic_similarity

score = semantic_similarity(
    "Chip stocks rally after upbeat AI demand",
    "Semiconductor shares rise as AI orders improve",
)

matches = rank_similar_texts(
    "defensive cash positioning",
    [
        "raise cash while volatility is elevated",
        "momentum rotation into chip makers",
    ],
    limit=1,
)

print(score)
print(matches[0].text)
```

## Profit Taker Calculator

Use `calculate_profit_taker_plan` to compute how many shares to sell in order to
recover your initial principal at the current market price.

```python
from risk_tools import calculate_profit_taker_plan

plan = calculate_profit_taker_plan(
    current_price=31.15,
    current_shares=420,
    initial_principal=10000,
)

print(plan.shares_to_sell)
print(plan.remaining_shares)
```

Optional dashboard copy for reinvestment ideas:

```python
from risk_tools import format_reinvestment_playbook

for item in format_reinvestment_playbook():
    st.write(f"- {item}")
```

> Educational tooling only — not financial advice.
