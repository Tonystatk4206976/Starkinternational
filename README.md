# Starkinternational

Fund analytics helpers.

## Sentiment Gauge

This repo includes a Plotly helper to render a market sentiment gauge.

```python
from sentiment_gauge import display_sentiment_gauge

fig = display_sentiment_gauge(0.42, compact=True)
fig.show()
```

For Streamlit:

```python
score = calculate_greed_score(headlines)
st.plotly_chart(display_sentiment_gauge(score, compact=True), use_container_width=True)
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


For compact UI cards/tables with the profit taker result:

```python
from risk_tools import calculate_profit_taker_plan, format_profit_taker_summary

plan = calculate_profit_taker_plan(31.15, 420, 10000)
summary = format_profit_taker_summary(plan)
for label, value in summary.items():
    st.metric(label, value)
```
