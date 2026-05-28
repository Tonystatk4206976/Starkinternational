# Starkinternational

Fund analytics helpers and a safe personal-finance aggregation foundation.

## Financial Aggregator Foundation

`financial_app.py` provides the first building blocks for a single financial
application that combines user-authorized financial exports from cloud storage
with public crypto wallet references.

Security boundaries are intentional:

- Cloud data should come from approved sync folders or a future OAuth flow for
  Google Drive, Microsoft OneDrive, and Dropbox.
- Crypto wallets are tracked by public Bitcoin or EVM-compatible addresses only.
- Private keys, extended private keys, and seed phrases are rejected before they
  can be stored or processed.

```python
from financial_app import CloudSource, WalletReference, build_profile

profile = build_profile(
    sources=[
        CloudSource("google_drive", "~/Google Drive/Finance"),
        CloudSource("onedrive", "~/OneDrive/Finance"),
        CloudSource("dropbox", "~/Dropbox/Finance"),
    ],
    wallets=[
        WalletReference(
            label="Main ETH",
            chain="ethereum",
            address="0x52908400098527886E0F7030069857D2E4169EE7",
        ),
    ],
)

print(profile.net_cashflow())
print(profile.spending_by_category())
```

Supported transaction export formats are CSV and JSON. Each transaction should
include a date (`date`, `posted_at`, or `transaction_date`), description
(`description`, `memo`, or `name`), and amount (`amount`, `value`, or `total`).
Optional fields include `currency`, `account`, and `category`.

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
