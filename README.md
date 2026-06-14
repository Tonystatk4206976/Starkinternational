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

## Wallet Cross-Reference Helper

Use `cross_reference_wallets` to identify wallet addresses that appear across
multiple evidence sources, spreadsheets, or case-review exports. Records are
dictionary-based so they can be loaded directly from CSV or JSON adapters.

```python
from wallet_cross_reference import (
    cross_reference_wallets,
    format_wallet_cross_reference_report,
)

records = [
    {"wallet": " 0xABC ", "source": "exchange export", "label": "defendant"},
    {"wallet": "0xabc", "source": "bank exhibit", "label": "defendant"},
    {"wallet": "0xdef", "source": "exchange export"},
]

for line in format_wallet_cross_reference_report(cross_reference_wallets(records)):
    print(line)
```

> Review support only — verify all addresses and source documents before legal use.

> Educational tooling only — not financial advice.
