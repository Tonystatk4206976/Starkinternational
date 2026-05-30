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

## GitHub Activity Merger

Use `merge_github_account_activity` to combine public GitHub event feeds for
multiple accounts into one newest-first timeline. Events are deduplicated by
GitHub event ID, which is useful when you want a single activity view for
separate personal, work, or legacy GitHub accounts.

```python
from github_activity import merge_github_account_activity, summarize_activity_by_account

activity = merge_github_account_activity(["octocat", "another-account"], pages=1)

for event in activity:
    print(event.created_at.isoformat(), event.account, event.event_type, event.repo)

print(summarize_activity_by_account(activity))
```

Set the `token` argument to a GitHub token when you need higher API rate limits.

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
