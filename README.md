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

> Educational tooling only — not financial advice.

## Wallet Cross-Reference

Use `cross_reference_wallets` to compare wallet identifiers from an external
reference list, such as complaint exhibits or discovery spreadsheets, with your
own known-wallet list. The helper is neutral: it does not include or verify any
real lawsuit allegations, and it only reports exact normalized overlaps between
the two datasets you provide.

```python
from wallet_reference import WalletRecord, cross_reference_wallets

reference_wallets = [
    WalletRecord("0xabc...123", source="Noah Doe lawsuit reference set"),
]
known_wallets = [
    WalletRecord("0xABC...123", source="my records", label="treasury wallet"),
]

matches = cross_reference_wallets(reference_wallets, known_wallets)
for match in matches:
    print(match.wallet, match.known_labels)
```

For a large reference set, such as 39,000 wallet rows, stream or load the rows
from your own CSV/export and pass the wallet column values into
`cross_reference_wallets`.
