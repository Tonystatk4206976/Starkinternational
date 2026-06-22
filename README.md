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

## Institutional Outreach RAG Workflow

This repository also includes a compliance-first RAG workflow for generating
organization-level or role-based financial outreach lists from permitted public
sources only. The workflow is designed for official institutional sources:

- company websites
- SEC EDGAR filings
- FINRA/BrokerCheck public firm records
- Federal Reserve/NIC institution records
- official press releases
- annual reports and proxy statements

It intentionally excludes LinkedIn scraping, social-network profiles, personal
contact brokers, household data, wealth labels, and personal contact dossiers.
Generated entries should stay at the institutional role level, such as
`Investor Relations — JPMorgan Chase` or `Corporate Secretary — Citigroup`.

```python
from institutional_rag import InstitutionalRagWorkflow, default_outreach_queries

workflow = InstitutionalRagWorkflow(
    allowed_company_domains={"jpmorganchase.com", "bankofamerica.com"}
)

for step in workflow.workflow_steps():
    print(step.name, step.compliance_gate)

queries = default_outreach_queries(["JPMorgan Chase", "Bank of America"])
print(queries)
```

